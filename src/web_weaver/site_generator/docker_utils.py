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
