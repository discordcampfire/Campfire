import discord
import asyncio

from discord.ext import commands
from typing import Union, Optional


class BannedUser(commands.Converter):
    '''Converter for finding banned users.'''

    async def convert(self, ctx, argument):
        '''Converts argument to a user object.'''
        banned_users = [entry.user for entry in await ctx.guild.bans()]
        user_name, user_discriminator = argument.split('#')

        user = discord.utils.get(banned_users, name=user_name, discriminator=user_discriminator)

        if user is not None:
            return user

        raise commands.BadArgument(message='Banned user not found')


class TimePeriod(commands.Converter):
    '''Converter for checking time intervals.'''

    async def convert(self, ctx, argument):
        '''Converts argument to a tuple representing a period of time.'''
        amount = argument[:-1]
        unit = argument[-1]

        if amount.isdigit() and unit in ['s', 'm', 'h', 'd', 'w', 'm', 'y']:
            return (int(amount), unit)

        raise commands.BadArgument(message='Not a valid period of time')


class Moderation(commands.Cog):
    '''Cog containing commands for server moderation.'''

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def kick(self, ctx, member: Union[discord.Member, int], *, 
                   reason=None):
        '''Kicks a member from the server.'''
        if isinstance(member, int):
            member = ctx.guild.get_member(member)

        await ctx.guild.kick(member, reason=reason)
        await ctx.send(f'{member} has been kicked.')

    @commands.command()
    async def ban(self, ctx, member: Union[discord.Member, int],
                  duration: Optional[TimePeriod]=None, *, reason=None):
        '''Bans a member from the server.'''
        if isinstance(member, int):
            member = ctx.guild.get_member(member)

        await ctx.guild.ban(member, reason=reason)

        if duration is None:
            await ctx.send(f'{member} has been banned.')
        else:
            await ctx.send(f'{member} has been temporarily banned.')

            multiplier = {
                's': 1,
                'm': 60,
                'h': 3600,
                'd': 86400,
                'w': 604800,
                'm': 2592000,
                'y': 31536000
            }

            amount, unit = duration
            await asyncio.sleep(amount * multiplier[unit])

            # Check if user is still banned
            def find_user(e):
                return e.user == member

            ban_entry = discord.utils.find(find_user, await ctx.guild.bans())

            if ban_entry is not None:
                await ctx.guild.unban(member, reason='Tempban expired')

    @commands.command()
    async def unban(self, ctx, user: Union[BannedUser, int], *, reason=None):
        '''Unbans a user from the server.'''
        bans = await ctx.guild.bans()

        if isinstance(user, int):
            banned_users = [entry.user for entry in bans]
            user = discord.utils.get(banned_users, id=user)

        user = discord.utils.get(bans, user=user).user
        await ctx.guild.unban(user, reason=reason)
        await ctx.send(f'{user} has been unbanned.')


def setup(bot):
    bot.add_cog(Moderation(bot))
