import discord
import asyncio

from discord.ext import commands
from typing import Optional


class BannedUserConverter(commands.Converter):
    '''Converter for finding banned users.'''

    async def convert(self, ctx, argument):
        '''Converts argument to a user object.'''
        banned_users = [entry.user for entry in await ctx.guild.bans()]

        # If argument could be a user id
        if argument.isdigit():
            user = discord.utils.get(banned_users, id=int(argument))
        else:

            # If argument is a users name
            if '#' not in argument:
                user = discord.utils.get(banned_users, name=argument)

            # If argument is a users name and discriminator
            else:
                user_name, user_discriminator = argument.split('#')
                user = discord.utils.get(banned_users, name=user_name, discriminator=user_discriminator)

        if user is not None:
            return user

        raise commands.UserNotFound(argument)


class DurationConverter(commands.Converter):
    '''Converter for checking time intervals.'''

    async def convert(self, ctx, argument):
        '''Converts argument to a tuple representing a period of time.'''
        amount = argument[:-1]
        unit = argument[-1]

        # Check if the amount is a digit and the unit is in the specified list
        if amount.isdigit() and unit in ['s', 'm', 'h', 'd', 'w', 'm', 'y']:
            return (int(amount), unit)

        raise commands.BadArgument(message='Not a valid period of time')


class Moderation(commands.Cog):
    '''Cog containing commands for server moderation.'''

    def __init__(self, bot):
        self.bot = bot
        self.sleep_multiplier = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800,
            'm': 2592000,
            'y': 31536000
        }

    async def handle_tempban(self, guild, member, duration):
        '''Unbans user once tempban expires.'''

        # If there is no duration, user hasn't been tempbanned
        if duration is not None:

            # Sleep for the duration
            amount, unit = duration
            await asyncio.sleep(amount * self.sleep_multiplier[unit])

            # Check if users are still banned. If so, unban
            if discord.utils.get(await guild.bans(), user=member) is not None:
                await guild.unban(member, reason='Tempban expired')

    async def throw_error(self, destination, message):
        '''Sends an error message.'''

        # Create error embed
        error_embed = discord.Embed(
            description=message,
            colour=discord.Colour.red()
        )

        await destination.send(embed=error_embed, delete_after=8)

    @commands.command(usage='kick <member> [reason]')
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: commands.MemberConverter, *, reason=None):
        '''Kicks a specified member from the server. A reason can be specified for the audit log, but is optional.'''

        # Kick member
        try:
            await ctx.guild.kick(member, reason=reason)
        except:
            await self.throw_error(ctx.channel, 'Failed to kick that member.')

        # Create embed
        embed = discord.Embed(
            description=f'Kicked `{member}`',
            colour=discord.Colour.orange(),
            timestamp=ctx.message.created_at
        )

        embed.set_author(name='Campfire', icon_url=self.bot.user.avatar_url)
        embed.add_field(name='Reason', value=f'```{reason}```', inline=False)
        embed.set_footer(text=f'Kicked by {ctx.author}', icon_url=ctx.author.avatar_url)

        await ctx.reply(embed=embed)

    @commands.command(usage='masskick <members...> [reason]')
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def masskick(self, ctx, members: commands.Greedy[commands.MemberConverter], *, reason=None):
        '''Kicks multiple members from the server. A reason can be specified for the audit log, but is optional.'''

        # If no members are specified
        if members == []:
            await ctx.message.delete()
            await self.throw_error(ctx.channel, 'Please specify at least one valid member to kick.')
            return

        # Create confirmation embed and check
        confirmation_embed = discord.Embed(
            description=f'Are you sure you would like to kick `{len(members)}` members? (Y/N)',
            colour=discord.Colour.orange()
        )

        def confirmation(msg):
            return msg.content.lower() in ['y', 'yes', 'n', 'no']

        # Send confirmation prompt and wait for response
        confirmation_prompt = await ctx.send(embed=confirmation_embed)
        confirmation_choice = await self.bot.wait_for('message', check=confirmation)

        # Delete confirmation prompt and response
        await confirmation_prompt.delete()
        await confirmation_choice.delete()

        # Continue only if confirmation was y or yes
        if confirmation_choice.content[0] == 'n':
            await ctx.message.delete()
            return

        # Try to kick all members and store the ones that were kicked
        kicked_members = members[:]
        for member in members:
            try:
                await ctx.guild.kick(member, reason=reason)
            except:
                kicked_members.remove(member)

        # Create string of kicked members
        kicked_members_string = '\n'.join([str(member) for member in kicked_members]) or None

        # Create final embed
        embed = discord.Embed(
            description=f'Successfully kicked `{len(kicked_members)}/{len(members)}` member(s)',
            colour=discord.Colour.orange(),
            timestamp=ctx.message.created_at
        )

        embed.set_author(name='Campfire', icon_url=self.bot.user.avatar_url)
        embed.add_field(name='Kicked members', value=f'```{kicked_members_string}```', inline=False)
        embed.add_field(name='Reason', value=f'```{reason}```', inline=False)
        embed.set_footer(text=f'Kicked by {ctx.author}', icon_url=ctx.author.avatar_url)

        await ctx.reply(embed=embed)

    @commands.command(usage='ban <member> [duration] [reason]')
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, member: commands.MemberConverter, duration: Optional[DurationConverter]=None, *, reason=None):
        '''Bans a specified member from the server. Optionally, a duration can be specified to make the ban temporary as well as a reason can be specified for the audit log.'''

        # Ban member
        try:
            await ctx.guild.ban(member, reason=reason)
        except:
            await self.throw_error(ctx.channel, 'Failed to ban that member.')

        # Create embed
        embed = discord.Embed(
            description=f'Banned `{member}`',
            colour=discord.Colour.orange(),
            timestamp=ctx.message.created_at
        )

        embed.set_author(name='Campfire', icon_url=self.bot.user.avatar_url)

        # Create field based on existence of tempban
        if duration is None:
            embed.add_field(name='Duration', value='```Permanent```')
        else:
            embed.add_field(name='Duration', value=f'```{duration[0]}{duration[1]}```')

        embed.add_field(name='Reason', value=f'```{reason}```', inline=False)
        embed.set_footer(text=f'Banned by {ctx.author}', icon_url=ctx.author.avatar_url)

        await ctx.reply(embed=embed)

        # Handle the tempban process if the member was banned for a specific duration
        await self.handle_tempban(ctx.guild, member, duration)

    @commands.command(usage='massban <members...> [duration] [reason]')
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def massban(self, ctx, members: commands.Greedy[commands.MemberConverter], duration: Optional[DurationConverter]=None, *, reason=None):
        '''Bans multiple members from the server. Optionally, a duration can be specified to make the ban temporary as well as a reason can be specified for the audit log.'''

        # If no members are specified
        if members == []:
            await ctx.message.delete()
            await self.throw_error(ctx.channel, 'Please specify at least one valid member to ban.')
            return

        # Create confirmation embed and check
        confirmation_embed = discord.Embed(
            description=f'Are you sure you would like to ban `{len(members)}` members? (Y/N)',
            colour=discord.Colour.orange()
        )

        def confirmation(msg):
            return ctx.author == msg.author and msg.content.lower() in ['y', 'yes', 'n', 'no']

        # Send confirmation prompt and wait for response
        confirmation_prompt = await ctx.send(embed=confirmation_embed)
        confirmation_choice = await self.bot.wait_for('message', check=confirmation)

        # Delete confirmation prompt and response
        await confirmation_prompt.delete()
        await confirmation_choice.delete()

        # Continue only if confirmation was y or yes
        if confirmation_choice.content[0] == 'n':
            await ctx.message.delete()
            return

        # Try to kick all members and store the ones that were kicked
        banned_members = members[:]
        for member in members:
            try:
                await ctx.guild.ban(member, reason=reason)
            except:
                banned_members.remove(member)

        # Create string of banned members
        banned_members_string = '\n'.join([str(member) for member in banned_members]) or None

        # Create final embed
        embed = discord.Embed(
            description=f'Successfully banned `{len(banned_members)}/{len(members)}` member(s)',
            colour=discord.Colour.orange(),
            timestamp=ctx.message.created_at
        )

        embed.set_author(name='Campfire', icon_url=self.bot.user.avatar_url)
        embed.add_field(name='Banned members', value=f'```{banned_members_string}```', inline=False)

        # Create field based on existence of tempban
        if duration is None:
            embed.add_field(name='Duration', value='```Permanent```')
        else:
            embed.add_field(name='Duration', value=f'```{duration[0]}{duration[1]}```')

        embed.add_field(name='Reason', value=f'```{reason}```', inline=False)
        embed.set_footer(text=f'Banned by {ctx.author}', icon_url=ctx.author.avatar_url)

        await ctx.reply(embed=embed)

        # Handle the tempban process if the members were banned for a specific duration
        await self.handle_tempban(ctx.guild, member, duration)

    @commands.command(usage='unban <user> [reason]')
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, user: BannedUserConverter, *, reason=None):
        '''Unbans a banned user from the server. A reason can be specified for the audit log, but is optional.'''

        # Ban user
        if discord.utils.get(await ctx.guild.bans(), user=user) is not None:
            await ctx.guild.unban(user, reason=reason)

        # Create embed
        embed = discord.Embed(
            description=f'Successfully unbanned `{user}`',
            colour=discord.Colour.orange(),
            timestamp=ctx.message.created_at
        )

        embed.set_author(name='Campfire', icon_url=self.bot.user.avatar_url)
        embed.add_field(name='Reason', value=f'```{reason}```', inline=False)
        embed.set_footer(text=f'Unbanned by {ctx.author}', icon_url=ctx.author.avatar_url)

        await ctx.reply(embed=embed)

    @commands.command(usage='clear [members...] [amount=100]')
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def clear(self, ctx, members: commands.Greedy[commands.MemberConverter], amount: int=100):
        '''
        Clears a specified number of messages from the channel. Optionally, multiple members can be specified to only delete messages created by those members as well as an amount of messages to search.

        The amount of messages is not the number of messages to delete but rather the number of previous messages to look through.
        '''

        # Delete the authors message
        await ctx.message.delete()

        # Delete all messages within limit
        if members == []:
            deleted = await ctx.message.channel.purge(limit=amount)

        # Delete all messages by targets
        else:

            def author_is_target(msg):
                '''Checks if a message is written by a target member.'''
                return msg.author in members

            deleted = await ctx.message.channel.purge(limit=amount, check=author_is_target)

        # If no messages are deleted
        if len(deleted) == 0:
            await self.throw_error(ctx.channel, 'There were no messages to delete.')
            return

        # Create embed
        embed = discord.Embed(
            description=f'`{len(deleted)}` messages deleted',
            colour=discord.Colour.orange(),
            timestamp=ctx.message.created_at
        )

        embed.set_author(name='Campfire', icon_url=self.bot.user.avatar_url)
        embed.set_footer(text=f'Cleared by {ctx.author}', icon_url=ctx.author.avatar_url)

        await ctx.send(embed=embed)

    @kick.error
    @ban.error
    async def kick_ban_errors(self, ctx, error):
        '''Error handler for kick and ban commands.'''

        # Delete authors message
        await ctx.message.delete()

        # If member is not specified or specified member is not found
        if isinstance(error, (commands.MissingRequiredArgument, commands.MemberNotFound)):
            await self.throw_error(ctx.channel, 'Please make sure you specify a valid server member.')

        # If author is missing permissions
        elif isinstance(error, commands.MissingPermissions):
            await self.throw_error(ctx.channel, 'You don\'t have permssion to do that.')

        else:
            raise error

    @masskick.error
    @massban.error
    async def mass_kick_ban_errors(self, ctx, error):
        '''Error handler for masskick and massban commands.'''

        # Delete authors message
        await ctx.message.delete()

        # If author is missing permissions
        if isinstance(error, commands.MissingPermissions):
            await self.throw_error(ctx.channel, 'You don\'t have permssion to do that.')

        else:
            raise error

    @unban.error
    async def unban_error(self, ctx, error):
        '''Error handler for unban command.'''

        # Delete authors message
        await ctx.message.delete()

        # If user is not specified or specified user is not banned
        if isinstance(error, (commands.MissingRequiredArgument, commands.UserNotFound)):
            await self.throw_error(ctx.channel, 'Please make sure you specify a valid banned user.')

        # If author is missing permissions
        elif isinstance(error, commands.MissingPermissions):
            await self.throw_error(ctx.channel, 'You don\'t have permssion to do that.')

        else:
            raise error

    @clear.error
    async def clear_error(self, ctx, error):
        '''Error handler for clear command.'''

        # Delete authors message
        await ctx.message.delete()

        # If the specified amount is not an integer
        if isinstance(error, commands.BadArgument):
            await self.throw_error(ctx.channel, 'Please make sure the amount you are specifying is a valid integer.')

        # If author is missing permissions
        elif isinstance(error, commands.MissingPermissions):
            await self.throw_error(ctx.channel, 'You don\'t have permssion to do that.')

        else:
            raise error


def setup(bot):
    bot.add_cog(Moderation(bot))
