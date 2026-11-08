# Proposed community activities

**Status: proposal only.** The games, schedules, slash commands, activity points,
and reminder settings below are not implemented. They describe a possible next
release for friends who enjoy memes, trivia, and chat activities.

The existing voice tracker, its configuration, levels, and lifetime leaderboard
keep their current behavior. These activities use a separate points table. No
voice totals or existing XP are reset or changed by this proposal.

## First release

Start with one five-question trivia round during the week, one weekend meme or
caption contest, and one weekly results post. Give each round a discussion thread
so answers, reactions, and friendly banter stay together. Let members join when
they have time; being online at the exact opening moment should not decide who
wins.

Suggested order after the compatibility and redirect work:

| Phase | Deliverable | Relative effort |
| --- | --- | --- |
| 1 | Five-question trivia, private answers, results, and persistent round state | Medium |
| 2 | Meme submissions, voting, and a results gallery | Medium |
| 3 | Monthly activity standings, hall of fame, and champion role | Medium |
| 4 | Theme polls, opt-in reminders, and member-submitted prompts | Small to medium |

These estimates describe size, not delivery dates. Automatic scheduling should
follow a few successful rounds started manually by a moderator.

## 1. Weekly trivia

### What friends experience

1. The bot posts a round card with the theme, closing time, and **Play trivia**
   button. A suggested first window is Wednesday 19:00 to Thursday 19:00 in the
   configured server timezone.
2. Each player receives five multiple-choice questions through private bot
   responses or forms. The questions have the same answers for everyone; option
   order may vary.
3. The bot confirms the submitted answers privately. It does not reveal whether
   an answer is correct while the round remains open.
4. At closing, the bot posts correct answers, short explanations, round standings,
   and a link to the discussion thread.

### Proposed commands

| Command | Who can use it | Result |
| --- | --- | --- |
| `/trivia play` | Members | Open the current round privately |
| `/trivia status` | Members | Show the current theme and deadline |
| `/trivia create` | Activity hosts | Prepare five questions and explanations as a draft |
| `/trivia open` | Activity hosts | Publish a reviewed draft |
| `/trivia close` | Activity hosts | Close submissions and publish results |
| `/trivia cancel` | Activity hosts | Cancel with a reason; award no points |

### Rules and points

- Five questions per round; four choices and one correct answer per question.
- Correct answer: **10 activity points**. Incorrect or unanswered: **0**.
- Maximum: **50 points per player per weekly round**. No speed bonus or daily
  streak bonus.
- One final submission per player. A confirmation step permits review before
  submitting. Duplicate clicks cannot award more points.
- Late submissions are rejected according to the bot's stored deadline.
- The person who wrote or reviewed the answers may play for fun but cannot earn
  points in that round. A normal host without answer access can compete.
- A host may remove a faulty question before results are finalized. Removed
  questions award zero to everyone and the results explain the change.

**Acceptance checks:** two players submitting at different times can earn equal
scores; answers remain private until closing; a restart retains submissions and
the deadline; closing twice produces only one set of points and one results post.

## 2. Weekly meme or caption contest

### What friends experience

1. A host posts a prompt, such as “Describe this week using one meme.” Suggested
   entries open Friday 19:00 and close Sunday 18:00.
2. **Submit entry** opens an image-and-caption form. Caption-only rounds use one
   shared image supplied by the host. A member can replace their entry until
   submissions close; only the latest version competes.
3. At the deadline, submissions freeze. The bot publishes numbered entries in a
   gallery and opens **Vote** until Sunday 21:00. Authors can be hidden from the
   gallery until results, while moderators can still identify the submitter.
4. Each voter privately selects one entry. The bot posts the winner, all entry
   authors, and final vote counts after voting closes.

### Proposed commands

| Command | Who can use it | Result |
| --- | --- | --- |
| `/meme submit` | Members | Submit or replace an entry before the deadline |
| `/meme withdraw` | Members | Remove their entry before voting starts |
| `/meme vote` | Members | Cast or change their one vote during voting |
| `/meme status` | Members | Show the prompt and current phase |
| `/meme create` | Activity hosts | Prepare a prompt and deadlines |
| `/meme open` | Activity hosts | Publish the contest |
| `/meme remove` | Moderators | Remove an entry with a recorded reason |
| `/meme cancel` | Activity hosts | Cancel with a reason; award no points |

### Rules and points

- One entry per member; the server's existing content rules apply.
- One vote per member, excluding their own entry. Changing a vote replaces it.
  Bots cannot enter or vote.
- Valid entry at the end: **10 participation points**. Winning entry: **40
  additional points**, giving a maximum of **50 points per weekly contest**.
- Voting itself awards no points. Equal highest vote counts produce joint
  winners, each receiving the winner bonus.
- Require at least two valid entries and three distinct eligible voters for a
  winner bonus. Otherwise award valid-entry participation points only.
- Host moderation decisions, cancellations, and removed votes have a reason in
  the host log. An entry removed before results earns no points.
- If an entry is removed during voting, votes for it are invalidated. Affected
  voters may vote again while the voting window remains open.
- If there are more entries than fit in one gallery, paginate the voting UI;
  every entry receives the same opportunity to be chosen.

**Acceptance checks:** a member cannot submit two competing entries or vote for
themselves; replacing a vote does not add a vote; entries cannot change after
voting starts; a restart preserves phase, entries, and votes; results are awarded
once. Describe votes as private from other members, not anonymous from the bot
operator.

## 3. Monthly activity seasons

Suggested defaults give trivia and memes equal maximum weight: **50 points each
per week**, or **100 points combined**. Extra practice rounds are marked
unscored. The limits apply even if hosts accidentally open extra scored rounds.

- `/season standings` shows the current monthly activity board and category
  breakdown. `/season history` shows past winners.
- Each scored round receives its season when it opens, using the configured
  server timezone. Its points stay in that season even if it closes next month.
- A new month opens a fresh board. Finalize the previous month after all rounds
  assigned to it close or are cancelled. Past seasons remain viewable.
- Highest total wins; equal totals produce joint champions, without an arbitrary
  tie-break based on who was online first.
- An optional **Community Champion** role lasts until the next season is
  finalized. It grants no moderation permissions. The bot needs Manage Roles and
  its own role must be above this role; standings still work if role assignment
  fails.
- Corrections require an administrator, a reason, and a visible adjustment log.
  Do not silently rewrite results. Existing voice time and XP remain independent.

**Acceptance checks:** a returning member starts on the same fresh board as
everyone else; round awards cannot be duplicated; the weekly category limits hold;
month boundaries and ties follow the rules above; existing voice records do not
change.

## 4. Member choices and optional reminders

- A host uses `/theme poll` to offer a few reviewed trivia categories or meme
  prompts. Native Discord polls suit this public preference vote.
- `/activities reminders on` and `/activities reminders off` manage an optional
  activity reminder role. Send at most one role notification when a round opens,
  and optionally one closing reminder if enabled. Never use `@everyone` for
  these activities.
- `/activities suggest` lets members submit a prompt or question privately for
  host review. Publish only accepted submissions. Do not automatically search
  friends' old messages for inside jokes.
- Let winners volunteer to suggest the next theme. Keep a fallback prompt so a
  round can continue if the winner is unavailable.

**Acceptance checks:** reminders go only to members who opted in; opting out
removes the role; restart recovery does not repeat notifications; suggestions
cannot publish a round without host review.

## Host permissions, scheduling, and settings

Activity hosts are members with Manage Server or an explicitly configured host
role. Removing another person's entry also requires Manage Messages or the
configured moderator role. Ordinary members cannot open, close, cancel, score,
or change a competition. Check permissions when an action is performed, including
when a button was posted before someone's permissions changed.

Suggested **future** settings (these names are not active configuration yet):

| Setting | Proposed default or purpose |
| --- | --- |
| `ACTIVITIES_ENABLED` | `false` until configured and tested |
| `ACTIVITIES_CHANNEL_ID` | Required destination for round and results cards |
| `ACTIVITIES_HOST_ROLE_ID` | Optional host role; Manage Server also grants access |
| `ACTIVITIES_REMINDER_ROLE_ID` | Optional notification role, without extra powers |
| `ACTIVITIES_CHAMPION_ROLE_ID` | Optional cosmetic winner role |
| `ACTIVITIES_TIMEZONE` | `Europe/Helsinki`; use an IANA timezone name |
| Trivia schedule | Wednesday 19:00; answers open for 24 hours |
| Meme schedule | Friday 19:00 entries; Sunday 18:00 voting; Sunday 21:00 results |
| Results schedule | One combined weekly recap after voting closes |

Store deadlines as UTC timestamps and show Discord's local-time timestamps to
members. Build recurring rounds from the selected local timezone so daylight
saving changes do not shift the advertised local opening hour. A repeated clock
time runs once, at its first occurrence; a nonexistent clock time moves to the
next valid local minute. The proposed evening schedule avoids these transition
hours.

After downtime, open no historical rounds. Finish an overdue open round once,
using its stored deadline, and schedule the next future round. Recover missed
results without sending a burst of reminder messages. A missing channel or
permission should pause publishing and produce a clear host log message.

## Information to save

Keep activity data outside tracked source files and separate from voice records.
Back it up with the bot's other runtime data. Store enough state to resume safely:

- Server ID, host/moderator roles, channel IDs, timezone, schedules, reminder
  preferences, and scoring settings.
- Round ID, season ID, type, prompt/questions, correct answers, host/reviewer
  IDs, phase, opening/closing times, and announcement/thread/message IDs.
- Trivia submissions keyed by round and member; meme entry caption/image
  references and member ID; one vote per round and member. Validate uploaded
  media type and size and retain an accessible copy through the contest and
  agreed archive period, rather than relying on an expiring attachment URL.
- Points awarded per round/member/category, weekly limits, result status, season
  winners, and reasoned adjustments. Use unique award IDs to prevent duplicate
  credit after a restart.
- Sent-notification records and moderation actions. Set a retention period for
  submissions and private answers; season totals and the hall of fame may outlive
  raw entries. Explain deletion requests to hosts before launch.

## Which Discord tools fit

Native polls are useful for choosing themes. Trivia needs private answers and a
timed reveal; meme voting needs one-vote and no-self-vote rules. Implement those
rules through the bot's buttons/forms and stored state. Do not assume a native
poll enforces the contest's custom rules. Native polls accept up to ten answers;
larger contests need a custom selection interface.

Image-upload forms and modern message galleries make a compact meme experience
possible. Put a native poll in its own message when also using Components V2,
because a V2 message cannot contain a native poll. A normal discussion thread is
enough initially; forum channels are an optional alternative for Community
servers.

A custom Discord Activity could eventually provide a shared visual quiz board
or drawing game. It is a separate hosted web application and is a later phase.
Current unverified Activity testing is restricted to invited testers/developers
and servers with fewer than 25 members, so assess distribution requirements
before committing to that direction.

Official platform references, checked for the proposal on 2026-11-07:

- [Discord Polls FAQ](https://support.discord.com/hc/en-us/articles/22163184112407-Polls-FAQ)
- [Discord component reference](https://docs.discord.com/developers/components/reference)
- [Discord components overview](https://docs.discord.com/developers/components/overview)
- [Forum Channels FAQ](https://support.discord.com/hc/en-us/articles/6208479917079-Forum-Channels-FAQ)
- [Activity testing and discovery](https://support-dev.discord.com/hc/en-us/articles/21204493235991-How-Can-Users-Discover-and-Play-My-Activity)

## Deciding whether to expand

Try a month of the small routine. Look at how many different friends participate,
how many return for another round, and whether results lead to conversation.
Keep host workload and opt-outs visible too. Defer currencies, shops, streaks,
unlimited automatic trivia, and a custom Activity until friends enjoy the basic
rounds enough to ask for more.
