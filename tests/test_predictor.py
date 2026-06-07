import pandas as pd

from connectors.data_layer import load_phase2_data
from models.predictor import MatchPredictor


def test_prediction_probabilities_sum_to_100():
    teams_df, _ = load_phase2_data()
    predictor = MatchPredictor(teams_df)
    pred = predictor.predict("Portugal", "Brazil")
    total = pred.home_win + pred.draw + pred.away_win
    assert 99.9 <= total <= 100.1
    assert pred.home_expected_goals >= 0
    assert pred.away_expected_goals >= 0
