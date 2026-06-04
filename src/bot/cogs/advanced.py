from __future__ import annotations

import base64
import hashlib
import json
import math
import random
import urllib.parse
import uuid
from statistics import mean

from disnake.ext import commands

from bot.core.command_aliases import register_multilingual_aliases
from bot.core.response_style import build_standard_embed

# mypy: ignore-errors


class AdvancedPrefixCog(commands.Cog):
    """Large advanced prefix command suite grouped by category."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        added = register_multilingual_aliases(self.bot, ("math", "text", "tools"))
        logger = getattr(self.bot, "logger", None)
        if logger is not None:
            logger.info("advanced_multilingual_aliases_registered", extra={"alias_count": added})

    async def _send(self, ctx: commands.Context, title: str, description: str) -> None:
        await ctx.send(embed=build_standard_embed(description, title=title))

    @commands.group(name="math", invoke_without_command=True)
    async def math_group(self, ctx: commands.Context) -> None:
        await self._send(ctx, "Math Category", "Use `math <subcommand>`. Run `help math`.")

    @math_group.command(name="add")
    async def math_add(self, ctx: commands.Context, a: float, b: float) -> None:
        await self._send(ctx, "Math Add", f"Result: `{a + b}`")

    @math_group.command(name="sub")
    async def math_sub(self, ctx: commands.Context, a: float, b: float) -> None:
        await self._send(ctx, "Math Subtract", f"Result: `{a - b}`")

    @math_group.command(name="mul")
    async def math_mul(self, ctx: commands.Context, a: float, b: float) -> None:
        await self._send(ctx, "Math Multiply", f"Result: `{a * b}`")

    @math_group.command(name="div")
    async def math_div(self, ctx: commands.Context, a: float, b: float) -> None:
        if b == 0:
            await self._send(ctx, "Math Divide", "Cannot divide by zero.")
            return
        await self._send(ctx, "Math Divide", f"Result: `{a / b}`")

    @math_group.command(name="mod")
    async def math_mod(self, ctx: commands.Context, a: float, b: float) -> None:
        if b == 0:
            await self._send(ctx, "Math Modulo", "Cannot modulo by zero.")
            return
        await self._send(ctx, "Math Modulo", f"Result: `{a % b}`")

    @math_group.command(name="pow")
    async def math_pow(self, ctx: commands.Context, a: float, b: float) -> None:
        await self._send(ctx, "Math Power", f"Result: `{a ** b}`")

    @math_group.command(name="sqrt")
    async def math_sqrt(self, ctx: commands.Context, value: float) -> None:
        if value < 0:
            await self._send(ctx, "Math Sqrt", "Cannot sqrt a negative number.")
            return
        await self._send(ctx, "Math Sqrt", f"Result: `{math.sqrt(value)}`")

    @math_group.command(name="abs")
    async def math_abs(self, ctx: commands.Context, value: float) -> None:
        await self._send(ctx, "Math Abs", f"Result: `{abs(value)}`")

    @math_group.command(name="ceil")
    async def math_ceil(self, ctx: commands.Context, value: float) -> None:
        await self._send(ctx, "Math Ceil", f"Result: `{math.ceil(value)}`")

    @math_group.command(name="floor")
    async def math_floor(self, ctx: commands.Context, value: float) -> None:
        await self._send(ctx, "Math Floor", f"Result: `{math.floor(value)}`")

    @math_group.command(name="round")
    async def math_round(self, ctx: commands.Context, value: float, digits: int = 2) -> None:
        await self._send(ctx, "Math Round", f"Result: `{round(value, digits)}`")

    @math_group.command(name="max")
    async def math_max(self, ctx: commands.Context, *values: float) -> None:
        if not values:
            await self._send(ctx, "Math Max", "Provide at least one value.")
            return
        await self._send(ctx, "Math Max", f"Result: `{max(values)}`")

    @math_group.command(name="min")
    async def math_min(self, ctx: commands.Context, *values: float) -> None:
        if not values:
            await self._send(ctx, "Math Min", "Provide at least one value.")
            return
        await self._send(ctx, "Math Min", f"Result: `{min(values)}`")

    @math_group.command(name="avg")
    async def math_avg(self, ctx: commands.Context, *values: float) -> None:
        if not values:
            await self._send(ctx, "Math Average", "Provide at least one value.")
            return
        await self._send(ctx, "Math Average", f"Result: `{mean(values)}`")

    @math_group.command(name="sum")
    async def math_sum(self, ctx: commands.Context, *values: float) -> None:
        if not values:
            await self._send(ctx, "Math Sum", "Provide at least one value.")
            return
        await self._send(ctx, "Math Sum", f"Result: `{sum(values)}`")

    @math_group.command(name="clamp")
    async def math_clamp(
        self,
        ctx: commands.Context,
        value: float,
        minimum: float,
        maximum: float,
    ) -> None:
        lower = min(minimum, maximum)
        upper = max(minimum, maximum)
        result = max(lower, min(value, upper))
        await self._send(ctx, "Math Clamp", f"Result: `{result}`")

    @math_group.command(name="percent")
    async def math_percent(self, ctx: commands.Context, value: float, total: float) -> None:
        if total == 0:
            await self._send(ctx, "Math Percent", "Total cannot be zero.")
            return
        result = (value / total) * 100
        await self._send(ctx, "Math Percent", f"Result: `{result:.2f}%`")

    @math_group.command(name="bmi")
    async def math_bmi(self, ctx: commands.Context, weight_kg: float, height_m: float) -> None:
        if height_m <= 0:
            await self._send(ctx, "Math BMI", "Height must be greater than zero.")
            return
        bmi = weight_kg / (height_m**2)
        await self._send(ctx, "Math BMI", f"Result: `{bmi:.2f}`")

    @commands.group(name="text", invoke_without_command=True)
    async def text_group(self, ctx: commands.Context) -> None:
        await self._send(ctx, "Text Category", "Use `text <subcommand>`. Run `help text`.")

    @text_group.command(name="upper")
    async def text_upper(self, ctx: commands.Context, *, value: str) -> None:
        await self._send(ctx, "Text Upper", value.upper())

    @text_group.command(name="lower")
    async def text_lower(self, ctx: commands.Context, *, value: str) -> None:
        await self._send(ctx, "Text Lower", value.lower())

    @text_group.command(name="title")
    async def text_title(self, ctx: commands.Context, *, value: str) -> None:
        await self._send(ctx, "Text Title", value.title())

    @text_group.command(name="reverse")
    async def text_reverse(self, ctx: commands.Context, *, value: str) -> None:
        await self._send(ctx, "Text Reverse", value[::-1])

    @text_group.command(name="length")
    async def text_length(self, ctx: commands.Context, *, value: str) -> None:
        await self._send(ctx, "Text Length", f"Length: `{len(value)}`")

    @text_group.command(name="words")
    async def text_words(self, ctx: commands.Context, *, value: str) -> None:
        words = [segment for segment in value.split() if segment]
        await self._send(ctx, "Text Words", f"Words: `{len(words)}`")

    @text_group.command(name="replace")
    async def text_replace(self, ctx: commands.Context, old: str, new: str, *, value: str) -> None:
        await self._send(ctx, "Text Replace", value.replace(old, new))

    @text_group.command(name="trim")
    async def text_trim(self, ctx: commands.Context, *, value: str) -> None:
        await self._send(ctx, "Text Trim", value.strip())

    @text_group.command(name="repeat")
    async def text_repeat(self, ctx: commands.Context, count: int, *, value: str) -> None:
        if count < 1 or count > 20:
            await self._send(ctx, "Text Repeat", "Count must be between 1 and 20.")
            return
        await self._send(ctx, "Text Repeat", value * count)

    @text_group.command(name="prefix")
    async def text_prefix(self, ctx: commands.Context, prefix_value: str, *, value: str) -> None:
        await self._send(ctx, "Text Prefix", f"{prefix_value}{value}")

    @text_group.command(name="suffix")
    async def text_suffix(self, ctx: commands.Context, suffix_value: str, *, value: str) -> None:
        await self._send(ctx, "Text Suffix", f"{value}{suffix_value}")

    @text_group.command(name="remove")
    async def text_remove(self, ctx: commands.Context, needle: str, *, value: str) -> None:
        await self._send(ctx, "Text Remove", value.replace(needle, ""))

    @text_group.command(name="count")
    async def text_count(self, ctx: commands.Context, needle: str, *, value: str) -> None:
        await self._send(ctx, "Text Count", f"Occurrences: `{value.count(needle)}`")

    @text_group.command(name="startswith")
    async def text_startswith(self, ctx: commands.Context, needle: str, *, value: str) -> None:
        await self._send(ctx, "Text Startswith", f"Result: `{value.startswith(needle)}`")

    @text_group.command(name="endswith")
    async def text_endswith(self, ctx: commands.Context, needle: str, *, value: str) -> None:
        await self._send(ctx, "Text Endswith", f"Result: `{value.endswith(needle)}`")

    @text_group.command(name="contains")
    async def text_contains(self, ctx: commands.Context, needle: str, *, value: str) -> None:
        await self._send(ctx, "Text Contains", f"Result: `{needle in value}`")

    @text_group.command(name="split")
    async def text_split(self, ctx: commands.Context, delimiter: str, *, value: str) -> None:
        parts = value.split(delimiter)
        await self._send(ctx, "Text Split", "\n".join(parts[:20]) or "No output.")

    @text_group.command(name="join")
    async def text_join(self, ctx: commands.Context, delimiter: str, *parts: str) -> None:
        if not parts:
            await self._send(ctx, "Text Join", "Provide at least one part to join.")
            return
        await self._send(ctx, "Text Join", delimiter.join(parts))

    @commands.group(name="tools", invoke_without_command=True)
    async def tools_group(self, ctx: commands.Context) -> None:
        await self._send(ctx, "Tools Category", "Use `tools <subcommand>`. Run `help tools`.")

    @tools_group.command(name="coinflip")
    async def tools_coinflip(self, ctx: commands.Context) -> None:
        await self._send(ctx, "Tools Coinflip", random.choice(["heads", "tails"]))

    @tools_group.command(name="roll")
    async def tools_roll(self, ctx: commands.Context, sides: int = 6) -> None:
        if sides < 2 or sides > 1000:
            await self._send(ctx, "Tools Roll", "Sides must be between 2 and 1000.")
            return
        await self._send(ctx, "Tools Roll", f"Result: `{random.randint(1, sides)}`")

    @tools_group.command(name="choose")
    async def tools_choose(self, ctx: commands.Context, *, options: str) -> None:
        choices = [option.strip() for option in options.split(",") if option.strip()]
        if len(choices) < 2:
            await self._send(ctx, "Tools Choose", "Provide at least two comma-separated options.")
            return
        await self._send(ctx, "Tools Choose", random.choice(choices))

    @tools_group.command(name="random")
    async def tools_random(self, ctx: commands.Context, minimum: int, maximum: int) -> None:
        low = min(minimum, maximum)
        high = max(minimum, maximum)
        await self._send(ctx, "Tools Random", f"Result: `{random.randint(low, high)}`")

    @tools_group.command(name="uuid")
    async def tools_uuid(self, ctx: commands.Context) -> None:
        await self._send(ctx, "Tools UUID", str(uuid.uuid4()))

    @tools_group.command(name="timestamp")
    async def tools_timestamp(self, ctx: commands.Context) -> None:
        import time

        current = int(time.time())
        await self._send(ctx, "Tools Timestamp", f"Unix: `{current}` | Discord: `<t:{current}:F>`")

    @tools_group.command(name="unixnow")
    async def tools_unixnow(self, ctx: commands.Context) -> None:
        import time

        await self._send(ctx, "Tools UnixNow", f"{int(time.time())}")

    @tools_group.command(name="base64encode")
    async def tools_base64encode(self, ctx: commands.Context, *, value: str) -> None:
        encoded = base64.b64encode(value.encode("utf-8")).decode("utf-8")
        await self._send(ctx, "Tools Base64 Encode", encoded)

    @tools_group.command(name="base64decode")
    async def tools_base64decode(self, ctx: commands.Context, *, value: str) -> None:
        try:
            decoded = base64.b64decode(value.encode("utf-8")).decode("utf-8")
        except Exception:
            await self._send(ctx, "Tools Base64 Decode", "Invalid base64 payload.")
            return
        await self._send(ctx, "Tools Base64 Decode", decoded)

    @tools_group.command(name="urlencode")
    async def tools_urlencode(self, ctx: commands.Context, *, value: str) -> None:
        await self._send(ctx, "Tools URL Encode", urllib.parse.quote(value))

    @tools_group.command(name="urldecode")
    async def tools_urldecode(self, ctx: commands.Context, *, value: str) -> None:
        await self._send(ctx, "Tools URL Decode", urllib.parse.unquote(value))

    @tools_group.command(name="md5")
    async def tools_md5(self, ctx: commands.Context, *, value: str) -> None:
        digest = hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()
        await self._send(ctx, "Tools MD5", digest)

    @tools_group.command(name="sha1")
    async def tools_sha1(self, ctx: commands.Context, *, value: str) -> None:
        digest = hashlib.sha1(value.encode("utf-8"), usedforsecurity=False).hexdigest()
        await self._send(ctx, "Tools SHA1", digest)

    @tools_group.command(name="sha256")
    async def tools_sha256(self, ctx: commands.Context, *, value: str) -> None:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        await self._send(ctx, "Tools SHA256", digest)

    @tools_group.command(name="colorhex")
    async def tools_colorhex(self, ctx: commands.Context, value: str) -> None:
        cleaned = value.strip().lstrip("#")
        if len(cleaned) != 6:
            await self._send(ctx, "Tools Color", "Provide a hex value like `1a2b3c`.")
            return
        try:
            red = int(cleaned[0:2], 16)
            green = int(cleaned[2:4], 16)
            blue = int(cleaned[4:6], 16)
        except ValueError:
            await self._send(ctx, "Tools Color", "Invalid hex value.")
            return
        await self._send(ctx, "Tools Color", f"RGB: `{red}, {green}, {blue}`")

    @tools_group.command(name="jsonpretty")
    async def tools_jsonpretty(self, ctx: commands.Context, *, value: str) -> None:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            await self._send(ctx, "Tools JSON", "Invalid JSON input.")
            return
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        if len(pretty) > 3500:
            pretty = pretty[:3500] + "\n..."
        await self._send(ctx, "Tools JSON", f"```json\n{pretty}\n```")


def setup(bot: commands.Bot) -> None:
    bot.add_cog(AdvancedPrefixCog(bot=bot))
