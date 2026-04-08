from config.settings import settings
from llm_generation.generator import RawPair


def passes_length(pair: RawPair) -> tuple[bool, str]:
    if len(pair.instruction.split()) < settings.min_instruction_length // 4:
        return False, "instruction_too_short"
    if len(pair.output) < settings.min_output_length:
        return False, "output_too_short"
    if len(pair.output) > settings.max_output_length:
        return False, "output_too_long"
    return True, ""
