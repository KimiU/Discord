###############################
# unitils.py - perus työkalut #
###############################
import re
from urllib.parse import urlsplit

NETTIX_SITES = ("nettiauto", "nettimarkkina", "nettimoto", "nettivene", "nettikone",
                "nettivaraosa", "nettivuokraus", "nettimokki", "nettikaravaani")

# Code detection must not fire on normal chat. The bot answers matches in public, so a false
# positive means scolding a friend for writing "good point" or "double kill". Only look for
# shapes that real code has and chat doesn't.
_CODE_SYNTAX = re.compile(
    r"```"                                                    # code block
    r"|\b(?:int|long|short|double|float|char|bool|boolean|byte|string|void)"
    r"(?:\[\])?\s+[a-z_]\w*(?:\[\])?(?:\s*=(?!=)|\s*;|\(|\[)"  # int x = / int[] a; / void main(
    r"|\bsystem\.out\.print|\bconsole\.log\(|\bprintf?\("     # print calls
    r"|^\s*#include\s*[<\"]"                                  # C/C++
    r"|^\s*def\s+\w+\s*\(.*\)\s*(?:->.*)?:\s*$"               # Python function
    r"|\b(?:public|private|protected)\s+(?:static\s+)?[\w<>\[\]]+\s+\w+\("  # Java/C# method
    r"|\b(?:for|while|if)\s*\(.*\)\s*\{",                     # for (...) {
    re.IGNORECASE | re.MULTILINE,
)
# Programming sites. Matched against the host and path, except "code", which is only matched
# against the host (leetcode.com, codepen.io) so "redeem-code" or "?code=" links don't count.
_CODE_LINK_WORDS = ("stackoverflow", "stackexchange", "w3schools", "jetbrains", "python",
                    "javascript", "java", "programming", "cppreference", "cplusplus", "csharp")
_URL = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)


def _is_code_link(url):
    try:
        parts = urlsplit(url.lower())
    except ValueError:
        return False
    host = parts.hostname or ""
    return "code" in host or any(word in host + parts.path for word in _CODE_LINK_WORDS)


# Tarkistaa sisältääkö viestissä koodia.
def isCode(msg):
    if _CODE_SYNTAX.search(msg):
        return True
    # Pasted code without a code block: several lines ending like statements/blocks.
    if sum(line.rstrip().endswith((";", "{", "}")) for line in msg.splitlines()) >= 2:
        return True
    return any(_is_code_link(url) for url in _URL.findall(msg))


def formatDuration(ms):
    """Milliseconds -> '12h 5m' / '5m 3s' / '42s'."""
    seconds = int(ms) // 1000
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


# Backwards-compatible name (the old function also took milliseconds despite its name).
convertSeconds = formatDuration
