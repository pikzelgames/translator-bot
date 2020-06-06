import discord
import base64
import json
import mysql.connector
import googletrans
import string

with open('credentials.json', 'r') as f:
    credentials = json.load(f)

db = mysql.connector.connect(host='localhost', user='translatorbot', database='translatorbot')
cursor = db.cursor()
db.autocommit = True

def query_db(query):
    cursor.execute(query)
    return list(cursor)

translator = googletrans.Translator()

client = discord.Client()

@client.event
async def on_message(message):
    if message.author.bot == True:
        return
    else:
        if message.guild == None:
            await message.channel.send('I can only accept commands in servers!')
            return
        else:
            server_prefix = query_db(f'SELECT prefix FROM serversettings WHERE serverid = "{message.guild.id}"')[0][0]

            if message.clean_content.startswith(server_prefix):
                split = message.content.split(' ')
                clean_split = message.clean_content.split(' ')

                if split[0][len(server_prefix):] == 'help':
                    if len(split) != 1:
                        await message.channel.send('Incorrect number of arguments! This command should have exactly 0 arguments.')
                        return
                    else:
                        embed=discord.Embed(title='Translator Help', description=server_prefix + 'help')
                        embed.add_field(name=f'{server_prefix}langcodes', value=f'Privately messages you the language codes required for {server_prefix}creategroup\nExample: {server_prefix}langcodes', inline=False)
                        embed.add_field(name=f'{server_prefix}creategroup (#channels) (langcodes)', value=f'Creates a new group of channels\nExample: {server_prefix}creategroup #general-en #general-da en da', inline=False)
                        embed.add_field(name=f'{server_prefix}deletegroup (group ID)', value=f'Deletes one or more existing groups\nExample: {server_prefix}deletegroup 1 3', inline=False)
                        embed.add_field(name=f'{server_prefix}showgroups', value=f'Lists all existing groups and their respective channels\nExample: {server_prefix}showgroups', inline=False)
                        embed.add_field(name=f'{server_prefix}blockuser (@users)', value=f'Adds one or more users to the blacklist\nExample: {server_prefix}blockuser @User1 @User2 @User3', inline=False)
                        embed.add_field(name=f'{server_prefix}unblockuser (@users)', value=f'Removes one or move users from the blacklist\nExample: {server_prefix}unblockuser @User1 @User3', inline=False)
                        embed.add_field(name=f'{server_prefix}showblacklist', value=f'Lists all users currently on the blacklist\nExample: {server_prefix}showblacklist', inline=False)
                        embed.add_field(name=f'{server_prefix}blockword (words)', value=f'Adds one or more words to the blacklist\nExample: {server_prefix}blockword banana strawberry apple', inline=False)
                        embed.add_field(name=f'{server_prefix}unblockword (words)', value=f'Removes one or more words from the blacklist\nExample: {server_prefix}unblockword apple strawberry', inline=False)
                        embed.add_field(name=f'{server_prefix}showblockedwords', value=f'Lists all words currently on the blacklist\nExample: {server_prefix}showblockedwords', inline=False)
                        await message.channel.send(embed=embed)
                elif split[0][len(server_prefix):] == 'prefix':
                    if not message.author.guild_permissions.manage_guild:
                        await message.channel.send('You need to have the **Manage Server** permission to do that!')
                        return
                    else:
                        if len(split) != 2:
                            await message.channel.send('Incorrect number of arguments! This command should have exactly 1 argument.')
                            return
                        else:
                            invalid = False
                            for char in list(clean_split[1]):
                                if char not in string.printable:
                                    invalid = True
                            
                            if invalid:
                                await message.channel.send('Invalid prefix!')
                                return
                            
                            query_db(f'UPDATE serversettings SET prefix = "{clean_split[1]}" WHERE serverid = \'{message.guild.id}\'')
                            
                            await message.channel.send(f'Command prefix updated to {clean_split[1]}')
                elif split[0][len(server_prefix):] == 'langcodes':
                    await message.channel.send('Check your messages!')

                    if message.author.dm_channel == None:
                        await message.author.create_dm()

                    await message.author.dm_channel.send('```Available language codes:\n' + '\n'.join([k.capitalize() + ': ' + v for k, v in googletrans.LANGCODES.items()]) + '```')
                elif split[0][len(server_prefix):] == 'creategroup':
                    if not message.author.guild_permissions.manage_guild:
                        await message.channel.send('You need to have the **Manage Server** permission to do that!')
                        return
                    else:
                        if len([x for x in message.channel_mentions if x.type == discord.ChannelType.text]) < 2:
                            await message.channel.send('Not enough text channels specified!')
                            return
                        else:
                            codes = [x for x in split[1:] if not x.startswith('<') and x != '' and x in googletrans.LANGCODES.values()]
                            if len(codes) < len(message.channel_mentions):
                                await message.channel.send('Not enough valid language codes!')
                                return
                            elif len(codes) > len(message.channel_mentions):
                                await message.channel.send('Too many valid language codes!')
                                return
                            else:
                                if len(list(set(codes))) < len(codes):
                                    await message.channel.send('There are duplicate language codes in your command! Every language code in a group must be unique.')
                                    return
                                if False in [message.guild.me.permissions_in(x).view_channel and message.guild.me.permissions_in(x).send_messages for x in message.channel_mentions]:
                                    await message.channel.send('I don\'t have permission to read or send messages in one of the specified channels!')
                                    return
                                else:
                                    if True in [str(x.id) in query_db(f'SELECT channels FROM serversettings WHERE serverid = "{message.guild.id}"')[0][0] for x in message.channel_mentions]:
                                        await message.channel.send('At lease one of these channels in already in a group!')
                                        return
                                    else:
                                        new_group = '-'.join([str(x.id) for x in message.channel_mentions if x.type == discord.ChannelType.text])
                                        current_channels = query_db(f'SELECT channels FROM serversettings WHERE serverid = "{message.guild.id}"')[0][0]
                                        query_db(f'UPDATE serversettings SET channels = "{new_group if current_channels == "" else current_channels + " " + new_group}" WHERE serverid = "{message.guild.id}"')
                                        
                                        new_langs = '-'.join(codes)
                                        current_channellangs = query_db(f'SELECT channellangs FROM serversettings WHERE serverid = "{message.guild.id}"')[0][0]
                                        query_db(f'UPDATE serversettings SET channellangs = "{new_langs if current_channellangs == "" else current_channellangs + " " + new_langs}" WHERE serverid = "{message.guild.id}"')

                                        pairs = zip(new_group.split('-'), new_langs.split('-'))
                                        await message.channel.send('Group created! The channels are:\n```' + \
                                            '\n'.join([message.guild.get_channel(int(x[0])).name + \
                                                (f' ({message.guild.get_channel(int(x[0])).category.name})' if message.guild.get_channel(int(x[0])).category != None else '') + \
                                                    f' - {googletrans.LANGUAGES[x[1]].capitalize()}' for x in pairs]) + '```')
                elif split[0][len(server_prefix):] == 'deletegroup':
                    if not message.author.guild_permissions.manage_guild:
                        await message.channel.send('You need to have the **Manage Server** permission to do that!')
                        return
                    else:
                        if len(split) != 2:
                            await message.channel.send('Incorrect number of arguments! This command should have exactly 1 argument.')
                            return
                        else:
                            if int(split[1]) not in range(len(query_db(f'SELECT channels FROM serversettings WHERE serverid = "{message.guild.id}"')[0][0].split(' '))):
                                await message.channel.send(f'Group number out of range! Use {server_prefix}showgroups to find the number of the group you want to delete.')
                                return
                            else:
                                current_channel_groups = query_db(f'SELECT channels FROM serversettings WHERE serverid = "{message.guild.id}"')[0][0].split(' ')
                                del current_channel_groups[int(split[1])]
                                query_db(f'UPDATE serversettings SET channels = "{" ".join(current_channel_groups)}" WHERE serverid = "{message.guild.id}"')

                                current_lang_groups = query_db(f'SELECT channellangs FROM serversettings WHERE serverid = "{message.guild.id}"')[0][0].split(' ')
                                del current_lang_groups[int(split[1])]
                                query_db(f'UPDATE serversettings SET channellangs = "{" ".join(current_lang_groups)}" WHERE serverid = "{message.guild.id}"')

                                await message.channel.send(f'Group {split[1]} deleted!')
                elif split[0][len(server_prefix):] == 'showgroups':
                    if query_db(f'SELECT channels FROM serversettings WHERE serverid = "{message.guild.id}"')[0][0] == '' or \
                        list(set(list(query_db(f'SELECT channels FROM serversettings WHERE serverid = "{message.guild.id}"')[0][0]))) == [' ']:
                        await message.channel.send(f'There are no groups in this server yet! Create some using {server_prefix}creategroup.')
                        return
                    else:
                        groups = [[zip(query_db(f'SELECT channels FROM serversettings WHERE serverid = "{message.guild.id}"')[0][0].split(' ')[x].split('-'), \
                            [googletrans.LANGUAGES[y].capitalize() for y in query_db(f'SELECT channellangs FROM serversettings WHERE serverid = "{message.guild.id}"')[0][0].split(' ')[x].split('-')])] \
                                for x in range(len(query_db(f'SELECT channels FROM serversettings WHERE serverid = "{message.guild.id}"')[0][0].split(' ')))]

                        await message.channel.send('```' + '\n\n'.join([f'{x}:\n' + '\n'.join(['\t' + message.guild.get_channel(int(list(y)[0])).name + \
                            (f' ({message.guild.get_channel(int(list(y)[0])).category.name})' if message.guild.get_channel(int(list(y)[0])).category != None else '') + ' - ' + list(y)[1] \
                                for y in groups[x][0]]) for x in range(len(query_db(f'SELECT channels FROM serversettings WHERE serverid = "{message.guild.id}"')[0][0].split(' ')))]) + '```')
                elif split[0][len(server_prefix):] == 'blockuser':
                    if not message.author.guild_permissions.manage_guild:
                        await message.channel.send('You need to have the **Manage Server** permission to do that!')
                        return
                    else:
                        if len(split) < 2:
                            await message.channel.send('Incorrect number of arguments! This command should have at least 1 argument.')
                            return
                        else:
                            if len(message.mentions) != len(split) - 1:
                                await message.channel.send('Incorrect number of user mentions! Every argument should be a mention.')
                                return
                            else:
                                if True in [str(x.id) in query_db(f'SELECT blacklist FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0] for x in message.mentions]:
                                    await message.channel.send('At least one of those users is already on the blacklist!')
                                    return
                                else:
                                    if message.guild.me in message.mentions:
                                        await message.channel.send('You can\'t blacklist me!')
                                        return
                                    else:
                                        current_users = query_db(f'SELECT blacklist FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0]
                                        new_users = ('' if current_users == '' else '-') + '-'.join([str(x.id) for x in message.mentions])

                                        query_db(f'UPDATE serversettings SET blacklist = "{current_users + new_users}" WHERE serverid = "{message.channel.guild.id}"')

                                        await message.channel.send(f'Added {"user" if message.mentions == 1 else "users"} {", ".join([x.name for x in message.mentions])} to the blacklist!')
                elif split[0][len(server_prefix):] == 'unblockuser':
                    if not message.author.guild_permissions.manage_guild:
                        await message.channel.send('You need to have the **Manage Server** permission to do that!')
                        return
                    else:
                        if len(split) < 2:
                            await message.channel.send('Incorrect number of arguments! This command should have at least 1 argument.')
                            return
                        else:
                            if len(message.mentions) != len(split) - 1:
                                await message.channel.send('Incorrect number of user mentions! Every argument should be a mention.')
                                return
                            else:
                                if False in [str(x.id) in query_db(f'SELECT blacklist FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0] for x in message.mentions]:
                                    await message.channel.send('Not all of those users are on the blacklist!')
                                    return
                                else:
                                    blacklist = query_db(f'SELECT blacklist FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0].split('-')
                                    for x in message.mentions:
                                        index = blacklist.index(str(x.id))
                                        del blacklist[index]

                                    query_db('UPDATE serversettings SET blacklist = "' + '-'.join(blacklist) + f'" WHERE serverid = "{message.channel.guild.id}"')
                                    
                                    await message.channel.send(f'Removed {"user" if message.mentions == 1 else "users"} {", ".join([x.name for x in message.mentions])} from the blacklist!')
                elif split[0][len(server_prefix):] == 'showblacklist':
                    if not message.author.guild_permissions.manage_guild:
                        await message.channel.send('You need to have the **Manage Server** permission to do that!')
                        return
                    else:
                        await message.channel.send('```Blacklist:\n' + '\n'.join([message.guild.get_member(int(x)).name for x in query_db(f'SELECT blacklist FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0].split('-') if x != '']) + '```')
                elif split[0][len(server_prefix):] == 'blockword':
                    if not message.author.guild_permissions.manage_guild:
                        await message.channel.send('You need to have the **Manage Server** permission to do that!')
                        return
                    else:
                        if len(split) < 2:
                            await message.channel.send('Incorrect number of arguments! This command should have at least 1 argument.')
                            return
                        else:
                            if True in [x in query_db(f'SELECT blockedwords FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0] for x in clean_split[1:]]:
                                await message.channel.send('At least one of those words is already blocked!')
                                return
                            else:
                                current_words = query_db(f'SELECT blockedwords FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0]
                                new_words = ('' if current_words == '' else '-') + '-'.join([x for x in clean_split[1:]])

                                query_db(f'UPDATE serversettings SET blockedwords = "{current_words + new_words}" WHERE serverid = "{message.channel.guild.id}"')

                                await message.channel.send(f'Blocked {"word" if len(clean_split) == 2 else "words"} {", ".join([x for x in clean_split[1:]])}!')
                elif split[0][len(server_prefix):] == 'unblockword':
                    if not message.author.guild_permissions.manage_guild:
                        await message.channel.send('You need to have the **Manage Server** permission to do that!')
                        return
                    else:
                        if len(split) < 2:
                            await message.channel.send('Incorrect number of arguments! This command should have at least 1 argument.')
                            return
                        else:
                            if False in [x in query_db(f'SELECT blockedwords FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0] for x in clean_split[1:]]:
                                await message.channel.send('Not all of those words are blocked!')
                                return
                            else:
                                word_blacklist = query_db(f'SELECT blockedwords FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0].split('-')
                                for x in clean_split[1:]:
                                    index = word_blacklist.index(x)
                                    del word_blacklist[index]

                                query_db('UPDATE serversettings SET blockedwords = "' + '-'.join(word_blacklist) + f'" WHERE serverid = "{message.channel.guild.id}"')
                                
                                await message.channel.send(f'Unblocked {"word" if len(clean_split) == 2 else "words"} {", ".join([x for x in clean_split[1:]])}!')
                elif split[0][len(server_prefix):] == 'showblockedwords':
                    if not message.author.guild_permissions.manage_guild:
                        await message.channel.send('You need to have the **Manage Server** permission to do that!')
                        return
                    else:
                        await message.channel.send('```Blocked words:\n' + '\n'.join([x for x in query_db(f'SELECT blockedwords FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0].split('-') if x != '']) + '```')
            elif str(message.channel.id) in query_db(f'SELECT channels FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0]:
                if len(message.clean_content) > 500:
                    await message.channel.send('This message won\'t be translated, as it is over 500 characters.')
                    return
                else:
                    if str(message.author.id) in query_db(f'SELECT blacklist FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0]:
                        return
                    else:
                        if True in [x in message.clean_content for x in query_db(f'SELECT blockedwords FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0].split('-') if x != '']:
                            return
                        else:
                            channel_groups = query_db(f'SELECT channels FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0].split(' ')
                            group_index = None
                            for i, v in enumerate(channel_groups):
                                if str(message.channel.id) in v:
                                    group_index = i
                                    break
                            channel_group = [int(x) for x in channel_groups[group_index].split('-')]
                            lang_group = query_db(f'SELECT channellangs FROM serversettings WHERE serverid = "{message.channel.guild.id}"')[0][0].split(' ')[group_index].split('-')
                            channel_index = channel_group.index(message.channel.id)

                            source_lang = lang_group[channel_index]

                            dest_channels = channel_group
                            del dest_channels[channel_index]

                            dest_langs = lang_group
                            del dest_langs[channel_index]

                            dest_info = list(zip(dest_channels, dest_langs))

                            for c, l in dest_info:
                                embed = discord.Embed(title=translator.translate('New message in #', src='en', dest=l).text + \
                                    message.channel.name + ((' (' + message.channel.category.name + ')') if message.channel.category != None else ''), color=message.author.color.value)
                                embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
                                embed.add_field(name=translator.translate('Source language:', src='en', dest=l).text + ' ' + translator.translate(googletrans.LANGUAGES[source_lang], src='en', dest=l).text, \
                                    value=translator.translate(message.clean_content, src=source_lang, dest=l).text, inline=False)
                                embed.set_footer(text=message.created_at.strftime('%H:%M %d/%m/%Y'))
                                await message.guild.get_channel(c).send(''.join([x.mention for x in message.mentions]), embed=embed)

@client.event
async def on_guild_join(guild):
    if len(query_db(f'SELECT * FROM serversettings WHERE serverid = "{guild.id}"')) > 0:
        query_db(f'DELETE FROM serversettings WHERE serverid = "{guild.id}"')
    query_db(f'INSERT INTO serversettings (serverid, prefix, channels, channellangs, blacklist, blockedwords) VALUES ("{guild.id}", "t!", "", "", "", "")')

@client.event
async def on_guild_remove(guild):
    query_db(f'DELETE FROM serversettings WHERE serverid = "{guild.id}"')

@client.event
async def on_guild_channel_delete(channel):
    if str(channel.id) in query_db(f'SELECT channels FROM serversettings WHERE serverid = "{channel.guild.id}"')[0][0]:
        current_channel_groups = query_db(f'SELECT channels FROM serversettings WHERE serverid = "{channel.guild.id}"')[0][0].split(' ')
        group_index = None
        for i, v in enumerate(current_channel_groups):
            if str(channel.id) in v:
                group_index = i
                break
        
        del current_channel_groups[group_index]
        query_db(f'UPDATE serversettings SET channels = "{" ".join(current_channel_groups)}" WHERE serverid = "{channel.guild.id}"')

        current_lang_groups = query_db(f'SELECT channellangs FROM serversettings WHERE serverid = "{channel.guild.id}"')[0][0].split(' ')
        del current_lang_groups[group_index]
        query_db(f'UPDATE serversettings SET channellangs = "{" ".join(current_lang_groups)}" WHERE serverid = "{channel.guild.id}"')

        if channel.guild.owner.dm_channel == None:
            await channel.guild.owner.create_dm()

        await channel.guild.owner.dm_channel.send(f'Someone just deleted a channel ({channel.name + (f" in the {channel.category.name} category" if channel.category != None else "")} in group {group_index} in your server, {channel.guild.name}. ' + \
            f'Because of this, I\'ve automatically deleted group {group_index}, to avoid any conflicts, but you can easily set it up again if you still want it.')

@client.event
async def on_guild_channel_update(before, channel):
    if str(channel.id) in query_db(f'SELECT channels FROM serversettings WHERE serverid = "{channel.guild.id}"')[0][0]:
        current_channel_groups = query_db(f'SELECT channels FROM serversettings WHERE serverid = "{channel.guild.id}"')[0][0].split(' ')
        group_index = None
        for i, v in enumerate(current_channel_groups):
            if str(channel.id) in v:
                group_index = i
                break
        
        if not (channel.guild.me.permissions_in(channel).view_channel and channel.guild.me.permissions_in(channel).send_messages):
            del current_channel_groups[group_index]
            query_db(f'UPDATE serversettings SET channels = "{" ".join(current_channel_groups)}" WHERE serverid = "{channel.guild.id}"')

            current_lang_groups = query_db(f'SELECT channellangs FROM serversettings WHERE serverid = "{channel.guild.id}"')[0][0].split(' ')
            del current_lang_groups[group_index]
            query_db(f'UPDATE serversettings SET channellangs = "{" ".join(current_lang_groups)}" WHERE serverid = "{channel.guild.id}"')

            if channel.guild.owner.dm_channel == None:
                await channel.guild.owner.create_dm()

            await channel.guild.owner.dm_channel.send(f'Someone just updated the permissions for a channel ({channel.name + (f" in the {channel.category.name} category" if channel.category != None else "")} ' + \
                f'in group {group_index} in your server, {channel.guild.name}). Now I don\'t have the correct access to it (I need read and write access to the channel). ' + \
                    f'Because of this, I\'ve automatically deleted group {group_index}, to avoid any conflicts, but you can easily set it up again if you still want it.')

client.run(base64.b64decode(credentials['bot-token']).decode('utf-8'))