/** Frozen experiment snapshot, copied without retraining from the source artifacts below.
 * Narrative: docs/MODEL_CARD_V1.md, TEMPORAL_BACKTESTING.md and individual model docs.
 * Historical evidence only; current registered identity/metrics come from the API.
 */
export interface Experiment {
  id: string;
  name: string;
  features: number;
  mae: number;
  rmse: number;
  r2: number;
  protocol: "exploratory-2025/26";
  lesson: string;
  outcome: string;
}
interface PooledMetrics {
  rows: number;
  mae: number;
  rmse: number;
  r2: number;
  negative_prediction_count: number;
  minimum_prediction_eur: number;
  maximum_prediction_eur: number;
  median_absolute_error_eur: number;
  worst_absolute_error_eur: number;
}
interface ModelHistory {
  experiments: Experiment[];
  folds: {
    fold: number;
    train: string[];
    test: string;
    trainRows: number;
    testRows: number;
    positionMaeChange: number;
  }[];
  pooled: PooledMetrics;
  per90Pooled: PooledMetrics;
  importance: { feature: string; gain: number }[];
  positionFamilyGain: number;
  sources: { path: string; sha256: string }[];
}
export const modelHistory = {
  experiments: [
    {
      id: "linear_regression",
      name: "Linear Regression",
      features: 4,
      mae: 11090195.645217676,
      rmse: 16832743.42046084,
      r2: 0.4528572436193363,
      protocol: "exploratory-2025/26",
      lesson: "Simple, interpretable starting point.",
      outcome: "Baseline",
    },
    {
      id: "ridge",
      name: "Ridge Regression",
      features: 4,
      mae: 11105366.505469473,
      rmse: 16933828.73249799,
      r2: 0.44626602255306136,
      protocol: "exploratory-2025/26",
      lesson: "Regularization did not improve held-out performance.",
      outcome: "No improvement",
    },
    {
      id: "random_forest",
      name: "Random Forest",
      features: 4,
      mae: 10135335.81789912,
      rmse: 16081107.851481052,
      r2: 0.5006296230295879,
      protocol: "exploratory-2025/26",
      lesson:
        "Nonlinearity mattered: MAE improved 8.6% over Linear Regression.",
      outcome: "Lower error",
    },
    {
      id: "xgboost",
      name: "XGBoost · four features",
      features: 4,
      mae: 10090465.83172123,
      rmse: 15947555.471390042,
      r2: 0.5088896467270392,
      protocol: "exploratory-2025/26",
      lesson: "A small additional improvement over Random Forest.",
      outcome: "Small improvement",
    },
    {
      id: "xgboost_with_position",
      name: "XGBoost + Position",
      features: 5,
      mae: 9993665.908482144,
      rmse: 15781526.954306262,
      r2: 0.519062225197896,
      protocol: "exploratory-2025/26",
      lesson: "A modest held-out gain; then checked across four seasons.",
      outcome: "Preferred after temporal checks",
    },
  ],
  folds: [
    {
      fold: 1,
      train: ["2021/22"],
      test: "2022/23",
      trainRows: 491,
      testRows: 522,
      positionMaeChange: -415360.0557650849,
    },
    {
      fold: 2,
      train: ["2021/22", "2022/23"],
      test: "2023/24",
      trainRows: 1013,
      testRows: 534,
      positionMaeChange: -24999.032786166295,
    },
    {
      fold: 3,
      train: ["2021/22", "2022/23", "2023/24"],
      test: "2024/25",
      trainRows: 1547,
      testRows: 543,
      positionMaeChange: -45385.0722836107,
    },
    {
      fold: 4,
      train: ["2021/22", "2022/23", "2023/24", "2024/25"],
      test: "2025/26",
      trainRows: 2090,
      testRows: 504,
      positionMaeChange: -96799.92323908582,
    },
  ],
  pooled: {
    rows: 2103,
    mae: 9677493.908571832,
    rmse: 15046414.97117625,
    r2: 0.5251604485345506,
    negative_prediction_count: 2,
    minimum_prediction_eur: -374349.53125,
    maximum_prediction_eur: 133754040.0,
    median_absolute_error_eur: 5881224.0,
    worst_absolute_error_eur: 111807272.0,
  },
  per90Pooled: {
    rows: 2103,
    mae: 9749592.38242429,
    rmse: 15060944.711892983,
    r2: 0.5242429373839617,
    negative_prediction_count: 1,
    minimum_prediction_eur: -572612.8125,
    maximum_prediction_eur: 125960288.0,
    median_absolute_error_eur: 5988754.0,
    worst_absolute_error_eur: 114128416.0,
  },
  importance: [
    {
      feature: "goals",
      gain: 0.2847890853881836,
    },
    {
      feature: "assists",
      gain: 0.19872048497200012,
    },
    {
      feature: "age",
      gain: 0.1382853239774704,
    },
    {
      feature: "minutes",
      gain: 0.08045436441898346,
    },
    {
      feature: "position_AM",
      gain: 0.055890485644340515,
    },
    {
      feature: "position_ST",
      gain: 0.04425210878252983,
    },
    {
      feature: "position_DM",
      gain: 0.0386386476457119,
    },
    {
      feature: "position_W",
      gain: 0.03355130925774574,
    },
    {
      feature: "position_FB",
      gain: 0.032708995044231415,
    },
    {
      feature: "position_CM",
      gain: 0.03226646035909653,
    },
    {
      feature: "position_CB",
      gain: 0.028736725449562073,
    },
    {
      feature: "position_UNKNOWN",
      gain: 0.023116134107112885,
    },
    {
      feature: "position_GK",
      gain: 0.008589865639805794,
    },
  ],
  positionFamilyGain: 0.2977507319301367,
  sources: [
    {
      path: "ml/models/model_metrics.json",
      sha256:
        "2559dfba6fe454773bdc99272f803b80ac6f9e3a5b8b06e71e435ebfcefe7f45",
    },
    {
      path: "ml/evaluation/temporal_backtest_summary.json",
      sha256:
        "0df6b306de31c74fc29833e32f3ffc4a6fa6841ed56eb5d1fd68b51c05697f0b",
    },
    {
      path: "ml/evaluation/per90_backtest_summary.json",
      sha256:
        "d060d9e94f641271046cac6e32deee7253da1af8e35ac0400cab3310a00acd62",
    },
    {
      path: "ml/models/playerworth_v1_feature_importance.json",
      sha256:
        "0fb84207c5698dfe5ffd1c4feed75a4d3c754bbc9c9cef83dafb2b701edcdaa3",
    },
  ],
} satisfies ModelHistory;
