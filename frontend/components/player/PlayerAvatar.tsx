import styles from "./PlayerAvatar.module.css";

export type PlayerAvatarSize = "xs" | "sm" | "md" | "hero";
export type PositionFamily = "GK" | "DEF" | "MID" | "ATT" | "UNKNOWN";
export type PlayerAvatarProps = {
  name: string;
  position?: string | null;
  size?: PlayerAvatarSize;
  className?: string;
};
const families: Record<string, PositionFamily> = {
  GK: "GK",
  GOALKEEPER: "GK",
  DEF: "DEF",
  CB: "DEF",
  LB: "DEF",
  RB: "DEF",
  FB: "DEF",
  WB: "DEF",
  LWB: "DEF",
  RWB: "DEF",
  "CENTRE-BACK": "DEF",
  "CENTER-BACK": "DEF",
  "LEFT-BACK": "DEF",
  "RIGHT-BACK": "DEF",
  DEFENDER: "DEF",
  MID: "MID",
  DM: "MID",
  CM: "MID",
  AM: "MID",
  LM: "MID",
  RM: "MID",
  "DEFENSIVE MIDFIELD": "MID",
  "CENTRAL MIDFIELD": "MID",
  "ATTACKING MIDFIELD": "MID",
  "LEFT MIDFIELD": "MID",
  "RIGHT MIDFIELD": "MID",
  MIDFIELDER: "MID",
  ATT: "ATT",
  ST: "ATT",
  CF: "ATT",
  W: "ATT",
  LW: "ATT",
  RW: "ATT",
  "CENTRE-FORWARD": "ATT",
  "CENTER-FORWARD": "ATT",
  "LEFT WINGER": "ATT",
  "RIGHT WINGER": "ATT",
  STRIKER: "ATT",
  FORWARD: "ATT",
};
export function positionFamily(position?: string | null): PositionFamily {
  const normalized = position?.trim().replace(/\s+/g, " ").toUpperCase() ?? "";
  return Object.hasOwn(families, normalized) ? families[normalized] : "UNKNOWN";
}
export function playerMonogram(name: string): string {
  const words = name
    .trim()
    .split(/\s+/)
    .filter((word) => /[\p{L}\p{N}]/u.test(word));
  const selected = words.length > 1 ? [words[0], words.at(-1)!] : words;
  const initials = selected
    .map((word) => word.match(/[\p{L}\p{N}]/u)?.[0] ?? "")
    .join("");
  return Array.from(initials.toUpperCase()).slice(0, 2).join("") || "—";
}
/** Decorative beside a written player name. Portrait rendering stays owned here. */
export function PlayerAvatar({
  name,
  position,
  size = "sm",
  className,
}: PlayerAvatarProps) {
  const family = positionFamily(position);
  const original = position?.trim() ?? "";
  const code = /^[a-z]{1,4}$/i.test(original)
    ? original.toUpperCase()
    : family === "UNKNOWN"
      ? "—"
      : family;
  const detailed = size === "md" || size === "hero";
  return (
    <span
      className={[styles.tile, styles[size], className]
        .filter(Boolean)
        .join(" ")}
      data-family={family}
      data-size={size}
      aria-hidden="true"
      title={original || undefined}
    >
      {detailed && <span className={styles.geometry} />}
      {size === "hero" && (
        <span className={styles.notation}>PW / PLAYER ID</span>
      )}
      <span className={styles.monogram}>{playerMonogram(name)}</span>
      {size !== "xs" && <span className={styles.position}>{code}</span>}
    </span>
  );
}
