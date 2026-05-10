import subprocess


class SiteGeneratorError(RuntimeError):
    pass


def image_exists(tag: str) -> bool:
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", tag],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except FileNotFoundError as error:
        raise SiteGeneratorError("Docker CLI not found. Install Docker first.") from error
    return result.returncode == 0


def image_label(tag: str, label: str) -> str | None:
    """Read a label off a Docker image. Returns None if the image is missing,
    the label key is unset, or docker reports `<no value>` (Go template fallback
    when the label key is absent from the labels dict).
    """
    try:
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                "{{ index .Config.Labels \"" + label + "\" }}",
                tag,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
        )
    except FileNotFoundError as error:
        raise SiteGeneratorError("Docker CLI not found. Install Docker first.") from error
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    if not value or value == "<no value>":
        return None
    return value


def run_docker_command(command: list[str]) -> None:
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as error:
        raise SiteGeneratorError("Docker CLI not found. Install Docker first.") from error
    except subprocess.CalledProcessError as error:
        raise SiteGeneratorError(
            f"Docker command failed with exit code {error.returncode}: "
            + " ".join(command)
        ) from error


def capture_docker_command(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as error:
        raise SiteGeneratorError("Docker CLI not found. Install Docker first.") from error
    except subprocess.CalledProcessError as error:
        raise SiteGeneratorError(
            f"Docker command failed with exit code {error.returncode}: "
            + " ".join(command)
            + f"\nSTDOUT:\n{error.stdout}\nSTDERR:\n{error.stderr}"
        ) from error
    return result.stdout.strip()
