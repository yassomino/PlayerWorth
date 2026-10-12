/** Mirrors backend/app/schemas.py. EUR amounts are JSON numbers; dates are ISO strings. */
export interface PlayerSearchResult {
  id: number;
  external_id: string;
  name: string;
  position: string | null;
  nationality: string | null;
  image_url: string | null;
  latest_season: string | null;
  latest_known_club: string | null;
}
export interface PlayerPage {
  items: PlayerSearchResult[];
  limit: number;
  offset: number;
}
export interface PlayerSeason {
  season: string;
  club: string | null;
  age: number | null;
  position: string | null;
  appearances: number;
  minutes: number;
  goals: number;
  assists: number;
  yellow_cards: number;
  red_cards: number;
  goals_per_90: number | null;
  assists_per_90: number | null;
  goal_contributions_per_90: number | null;
  clubs_in_season: number;
  season_end_date: string;
}
export interface MarketValue {
  value_eur: number;
  value_date: string;
  source: string;
}
export interface PlayerDetail {
  player: PlayerSearchResult & { date_of_birth: string | null };
  seasons: PlayerSeason[];
  market_values: MarketValue[];
}
export interface ModelInputs {
  age: number;
  minutes: number;
  goals: number;
  assists: number;
  position: string | null;
}
export interface ModelIdentity {
  model_name: string;
  model_version: string;
}
export interface PredictionResponse extends ModelIdentity {
  input: ModelInputs;
  predicted_value_eur: number;
  prediction_id: number | null;
}
export interface PlayerPrediction extends PredictionResponse {
  player_id: number;
  season: string;
  observed_value_eur: number | null;
  difference_eur: number | null;
}
export interface SimulationResponse extends ModelIdentity {
  player_id: number;
  season: string;
  prediction_id: number | null;
  difference_eur: number;
  baseline: { inputs: ModelInputs; predicted_value_eur: number };
  simulation: { inputs: ModelInputs; predicted_value_eur: number };
}
export interface RegisteredModel extends ModelIdentity {
  model_type: string;
  feature_list: string[];
  evaluation_method: string;
  mae: number | null;
  rmse: number | null;
  r2: number | null;
  median_absolute_error: number | null;
  is_production: boolean;
}
export interface ModelResponse extends RegisteredModel {
  training_seasons: string[];
  training_row_count: number;
  evaluation_row_count: number;
  limitations: string[];
}
export interface RankingPlayer {
  rank: number;
  player_id: number;
  player_name: string;
  club: string | null;
  position: string | null;
  season: string;
  observed_value_eur: number;
  predicted_value_eur: number;
  difference_eur: number;
}
export interface RankingResponse extends ModelIdentity {
  season: string;
  eligible_rows: number;
  excluded_rows: number;
  description: string;
  items: RankingPlayer[];
}
