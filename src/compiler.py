import re
import subprocess
import tempfile
from pathlib import Path


class BlueprintCompiler:
    @staticmethod
    def remove_xml_header(xml_text: str) -> str:
        pattern = r"<!--\s*DO NOT EDIT!.*?-->\n?"
        return re.sub(pattern, "", xml_text, flags=re.DOTALL)

    @classmethod
    def process(cls, text: str, direction: str) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input"
            output_file = Path(tmpdir) / "output"

            input_file.write_text(text)

            subprocess.run(
                [
                    "blueprint-compiler",
                    direction,
                    str(input_file),
                    "--output",
                    str(output_file),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            output_text = output_file.read_text()

            if direction == "compile":
                return cls.remove_xml_header(output_text)

            return output_text
