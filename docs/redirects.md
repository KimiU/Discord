# Redirect rules

Redirects now **suggest a channel by default**. A matching message stays where it was posted,
with its original text, attachments and conversation intact. The bot replies with a channel
suggestion. Existing Nettix and code targets remain available as default rules.

## Configure from Discord

Use your configured command prefix (the examples use `!`). All `redirect` commands require
the server-level **Manage Server** permission, including list and test. They do not work in DMs.
Changes take effect immediately and survive restarts.

```text
!redirect
!redirect add cars #nettimauto domain nettiauto.com
!redirect add coding #nörttiluola code
!redirect add memes #memes keyword meme of the week
!redirect source memes #general
!redirect test https://www.nettiauto.com/Example/ABC
!redirect toggle memes off
!redirect remove memes
```

Choose actual channels from your server when typing `#channel`. Rule names use 1–32 lowercase
letters, numbers, underscores or hyphens, starting with a letter. Adding an existing name
updates its target and matching condition, while keeping its source, mode and enabled state.

| Command | Purpose |
| --- | --- |
| `!redirect`, `!redirect list` | Show current settings and available rules |
| `!redirect add <name> <#target> <type> [pattern]` | Add or update a rule |
| `!redirect remove <name>` | Remove a rule, including a default rule |
| `!redirect enable`, `!redirect disable` | Enable or disable redirects for this server |
| `!redirect mode suggest` | Default action: `suggest`, `copy`, or `move` |
| `!redirect cooldown 300` | Seconds between actions for a member in a source channel; 0–86400 |
| `!redirect source <name> [#channel]` | Limit a rule to a source channel and its threads; omit channel to clear |
| `!redirect rulemode <name> <mode>` | Override a rule's mode; use `default` to inherit the server setting |
| `!redirect toggle <name> on` | Enable a rule; use `off` to disable it |
| `!redirect test <text>` | Preview the first matching rule in this channel without taking action |

Match types:

- `domain`: matches an HTTP(S) link's exact hostname or a subdomain. `example.com` matches
  `www.example.com`, but not `notexample.com`, a query mentioning example.com, or
  `example.com.evil.test`. Supply a hostname, without `https://` or a URL path.
- `keyword`: case-insensitive phrase anywhere in the message. The remaining command text is
  the phrase, so multiple words do not need quotes.
- `code`: the existing code-fence, programming-keyword and programming-link detector.
- `nettix`: links to the existing Nettix .com domains and their subdomains.

Rules run in listed order; the first eligible match wins. There can be at most 100 rules.
A message in the destination or one of its threads is skipped. Bot/webhook messages, DMs,
and messages starting with the command prefix are skipped. The cooldown is shared across rules
for each member/source channel, so multiple matching rules do not create duplicate reminders.
Cooldown timestamps reset when the bot restarts.

## Choose an action

- **suggest**: reply with the destination channel; keep the original message.
- **copy**: post the original text with author attribution and an original-message link.
  Attachments are re-uploaded with their spoiler marking; the source remains in place.
- **move**: post the original text and re-upload every attachment, then delete the source
  only after the destination send succeeds. Requires **Manage Messages** and **Read Message History** at the source,
  plus destination **Attach Files** when files are present.

All generated messages disable mentions, so copying `@everyone`, a role, or a user does not
ping them again. Copy and move require destination **View Channel**, **Send Messages** and
**Embed Links**. The author must also be able to view the destination. Cross-server targets
are ignored. Restricted source channels and private threads always receive a suggestion
instead of having their content copied elsewhere. Age-restricted content cannot be copied
or moved into an unrestricted channel. Spoiler attachments keep their spoiler marking.
Both copy and move need **Attach Files** when files are present and fall back to a suggestion
if the files exceed the upload limit or cannot be uploaded with current permissions.

Move falls back to a suggestion for replies, stickers, polls, message components, text over
2000 characters, or attachments that exceed the server's upload limit or cannot be uploaded
with current permissions. A failed upload/send leaves the original untouched. If sending
succeeds but deletion fails, both copies remain and the failure is logged. Copy supports text
up to 4000 characters; longer content receives a suggestion. Suggestions need permission to
send/reply in the source channel. Missing source permissions are logged without deleting anything.
Before deletion the bot fetches the source again; if it changed during copying or cannot be
checked, it keeps the source. Discord does not provide an atomic conditional-delete operation.

## Configure defaults in .env

Copy the new entries from `.env.example` to your existing private `.env`. Keep your current
token, scoring options, channel IDs, and other settings. Restart after changing `.env`.

```dotenv
REDIRECT_ENABLED=true
REDIRECT_MODE=suggest
REDIRECT_COOLDOWN_SECONDS=300
REDIRECT_RULES_FILE=./data/redirects.json
REDIRECT_RULES_JSON=[]
NETTIAUTO_CHANNEL_ID=788403517231595571
CODE_CHANNEL_ID=755053446763380767
```

Leave a built-in target empty to omit that default rule. To supply extra default rules in
the environment, use a single-quoted JSON array (replace example IDs with your channels):

```dotenv
REDIRECT_RULES_JSON='[{"name":"screenshots","target_channel_id":123456789012345678,"match_type":"keyword","pattern":"screenshot","mode":"suggest","source_channel_id":234567890123456789,"enabled":true}]'
```

Required fields are `name`, `target_channel_id`, and `match_type`. `pattern` is required for
domain/keyword rules. Optional fields are `mode` (default: inherit), `source_channel_id`
(default: any source), and `enabled` (default: true). A custom default with name `nettix` or
`code` replaces that built-in default.

**Precedence:** `.env` supplies defaults until the first chat configuration change in a
server. That change saves the server's complete settings and rule list to `REDIRECT_RULES_FILE`.
Its saved configuration then takes precedence over `.env`, including across restarts.
Other servers keep their own saved settings or the environment defaults. Removing a default
rule in chat stays removed. To change a configured server, use chat commands; changing `.env`
does not overwrite its saved settings. `REDIRECT_ENABLED` is an initial default, not a global
kill switch; use `!redirect disable` in each configured server when needed.

Back up the configured rules file alongside member stats. The default path and its temporary
file are ignored by Git. If you choose a different path, keep that runtime file out of source
control too. Invalid rule JSON or saved configuration stops redirect initialization with a
clear error, instead of replacing the file. Fix the configuration and restart.
