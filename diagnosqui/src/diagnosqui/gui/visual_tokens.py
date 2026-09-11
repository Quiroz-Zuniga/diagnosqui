"""Tokens independientes de Qt, contraste y variantes de plataforma."""

from __future__ import annotations

from dataclasses import asdict, dataclass

COLORS = {"NORMAL": "#218739", "ADVERTENCIA": "#B77900", "CRITICO": "#C42B1C"}
PALETTES = {
    "windows": (
        "#F5F6F8",
        "#FFFFFF",
        "#EEF1F5",
        "#1F2937",
        "#667085",
        "#0078D4",
        "#E5F2FB",
        "#D9DEE7",
    ),
    "ubuntu": (
        "#F7F5F4",
        "#FFFFFF",
        "#F1EEEC",
        "#292525",
        "#6F6763",
        "#E95420",
        "#FCEBE5",
        "#DDD8D5",
    ),
    "debian": (
        "#F6F5F7",
        "#FFFFFF",
        "#F0EEF3",
        "#292631",
        "#706B78",
        "#A80030",
        "#F6E5EA",
        "#DDD9E1",
    ),
    "linux": (
        "#F5F6F5",
        "#FFFFFF",
        "#EEF0EE",
        "#252A27",
        "#68706B",
        "#3A7D5D",
        "#E6F1EB",
        "#D9DEDB",
    ),
}


def luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        part / 12.92 if part <= 0.04045 else ((part + 0.055) / 1.055) ** 2.4
        for part in channels
    ]
    return sum(part * weight for part, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast_ratio(first: str, second: str) -> float:
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def readable_color(color: str, background: str, minimum: float = 4.5) -> str:
    """Deriva una tinta de la misma familia cuando el token no tiene contraste."""
    if contrast_ratio(color, background) >= minimum:
        return color
    target = 0 if luminance(background) > 0.18 else 255
    channels = [int(color[index : index + 2], 16) for index in (1, 3, 5)]
    for step in range(1, 101):
        adjusted = "#" + "".join(
            f"{round(value + (target - value) * step / 100):02X}" for value in channels
        )
        if contrast_ratio(adjusted, background) >= minimum:
            return adjusted
    return "#000000" if target == 0 else "#FFFFFF"


@dataclass(frozen=True)
class VisualTokens:
    bg: str
    surface: str
    sidebar: str
    text_primary: str
    text_secondary: str
    accent: str
    accent_soft: str
    border: str
    mode: str = "light"
    radius: int = 5
    spacing: int = 12
    font_size: int = 13

    @property
    def accent_ink(self) -> str:
        return readable_color(self.accent, self.accent_soft)

    @property
    def on_accent(self) -> str:
        return "#FFFFFF" if contrast_ratio(self.accent, "#FFFFFF") >= 4.5 else "#000000"

    @property
    def focus(self) -> str:
        return readable_color(self.accent, self.bg, 3)

    def state_ink(self, state: str) -> str:
        return readable_color(COLORS.get(state, self.text_secondary), self.surface)

    def substitutions(self) -> dict[str, object]:
        return dict(
            asdict(self),
            accent_ink=self.accent_ink,
            on_accent=self.on_accent,
            focus=self.focus,
            normal=self.state_ink("NORMAL"),
            warning=self.state_ink("ADVERTENCIA"),
            critical=self.state_ink("CRITICO"),
        )


def build_tokens(platform: str = "linux", mode: str = "light") -> VisualTokens:
    base = PALETTES.get(platform, PALETTES["linux"])
    if mode != "dark":
        return VisualTokens(*base)
    # El acento mantiene su identidad; superficies neutrales sin negro ni neón.
    return VisualTokens(
        "#242629",
        "#2D3034",
        "#272A2E",
        "#F0F1F2",
        "#B7BDC5",
        base[5],
        "#383D44",
        "#51575F",
        mode="dark",
    )
