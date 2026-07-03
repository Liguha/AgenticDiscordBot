"""View detailed information about available commands."""

from discord import app_commands, Interaction, Message, Client
from .base import MessageCommand, InteractionCommand
from ....events import EventBroker
from ....state_types import PrefixState

__all__ = ["message_help", "interaction_help"]

ARGS_DESC = {
    "command": "The specific command name to look up details for"
}

async def command_autocomplete(interaction: Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=name, value=name)
        for name in InteractionCommand.COMMANDS
        if current.lower() in name.lower()
    ][:25]

@MessageCommand.add_descriptions(**ARGS_DESC)
@MessageCommand.with_name("help", "prefix")
async def message_help(broker: EventBroker, client: Client, message: Message, state: PrefixState, command: str | None = None) -> PrefixState:
    if not command:
        lines = [f"**Message prefix**: `{state.prefix}`", "**Available Commands:**"]
        for name, cmd in MessageCommand.COMMANDS.items():
            doc = cmd.__doc__.strip().split("\n")[0] if cmd.__doc__ else "No description provided."
            lines.append(f"  `{state.prefix}{name}` — {doc}")
        await message.reply("\n".join(lines))
    else:
        if command in MessageCommand.COMMANDS:
            cmd = MessageCommand.COMMANDS[command]
            await message.reply(f"```\n{cmd.help}\n```")
        else:
            await message.reply(f"Command `{command}` does not exist.")
    return state


@app_commands.describe(**ARGS_DESC)
@app_commands.autocomplete(command=command_autocomplete)
@InteractionCommand.with_name("help", "prefix")
async def interaction_help(broker: EventBroker, interaction: Interaction, state: PrefixState, command: str | None = None) -> PrefixState:
    if not command:
        lines = [f"**Message prefix**: `{state.prefix}`", "**Available Commands:**"]
        for name, cmd in InteractionCommand.COMMANDS.items():
            doc = cmd.__doc__.strip().split("\n")[0] if cmd.__doc__ else "No description provided."
            lines.append(f"  `/{name}` — {doc}")
        await interaction.followup.send("\n".join(lines))
    else:
        if command in InteractionCommand.COMMANDS:
            msg_cmd = MessageCommand.COMMANDS.get(command)
            help_text = msg_cmd.help if msg_cmd else "Detailed information unavailable."
            await interaction.followup.send(f"```\n{help_text}\n```")
        else:
            await interaction.followup.send(f"Command `{command}` does not exist.")
    return state