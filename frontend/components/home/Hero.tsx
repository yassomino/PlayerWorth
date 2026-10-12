import { PlayerSearch } from "../search/PlayerSearch";
export function Hero() {
  return (
    <section className="hero container" aria-labelledby="hero-title">
      <div className="hero-copy">
        <div className="eyebrow hero-kicker">
          <span className="status-dot" /> FOOTBALL ANALYTICS / PLAYERWORTH
        </div>
        <h1 id="hero-title">
          THE GAME.
          <br />
          <span>ANOTHER VALUE.</span>
        </h1>
        <p className="hero-description">
          What does the model think a footballer is worth? Search a Premier
          League player and explore estimates built from historical performance.
        </p>
        <PlayerSearch />
      </div>
      <div className="pitch-panel" aria-hidden="true">
        <div className="pitch-top">
          <span>PLAYERWORTH / ANALYTICS</span>
          <span>FIVE INPUTS. A DIFFERENT PERSPECTIVE.</span>
        </div>
        <div className="pitch">
          <div className="pitch-half" />
          <div className="pitch-circle" />
          <div className="penalty top" />
          <div className="penalty bottom" />
          <div className="pitch-point p1" />
          <div className="pitch-point p2" />
          <div className="pitch-point p3" />
          <div className="pitch-point p4" />
          <div className="pitch-point p5" />
          <span className="pitch-label label-a">PERFORMANCE</span>
          <span className="pitch-label label-b">PERSPECTIVE</span>
        </div>
        <div className="pitch-bottom">
          <span>FOOTBALL, IN FOCUS.</span>
          <span>↗</span>
        </div>
      </div>
    </section>
  );
}
