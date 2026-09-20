from datetime import datetime
from nba_api.stats.endpoints import leaguedashplayerstats

def get_current_nba_season():
    now = datetime.now()
    start_year = now.year if now.month >= 10 else now.year - 1
    end_year_short = str(start_year + 1)[-2:]
    return f"{start_year}-{end_year_short}"

def calculate_parlay_probability(prob_list):
    """
    Calculate the probability of winning a parlay bet given individual probabilities.
    """
    overall_probability = 1.0
    for prob in prob_list:
        overall_probability *= prob
    return overall_probability

def calculate_ev(win_prob, decimal_odds, stake=1.0):
    """
    Calculate expected value (EV) per stake.
    """
    net_profit = stake * (decimal_odds - 1)
    loss = stake
    ev = (win_prob * net_profit) - ((1 - win_prob) * loss)
    return round(ev, 2)

def evaluate_ticket(props_list, stake=10.0):
    probabilities = [prop["prob"] for prop in props_list]
    combined_prob = calculate_parlay_probability(probabilities)

    combined_odds = 1.0
    for prop in props_list:
        combined_odds *= prop.get("odds", 1.0)

    ticket_ev = calculate_ev(combined_prob, combined_odds, stake)

    return {
        "combined_prob": combined_prob,
        "combined_odds": combined_odds,
        "ticket_ev": ticket_ev,
    }

def scan_top_performers(stat="PTS", min_minutes=25.0, min_games=8, top_n=10):
    """
    Pulls league-wide data for the last 10 games in a single API call.
    """
    current_season = get_current_nba_season()
    dash = leaguedashplayerstats.LeagueDashPlayerStats(
        season=current_season,
        last_n_games=10,
        per_mode_detailed='PerGame',
        season_type_all_star='Regular Season'
    )
    df = dash.get_data_frames()[0]

    df = df[(df["MIN"] >= min_minutes) & (df["GP"] >= min_games)]

    ranked = df[["PLAYER_NAME", "TEAM_ABBREVIATION", "GP", "MIN", stat]].sort_values(
        by=stat, ascending=False
    ).head(top_n)

    return ranked[["PLAYER_NAME", "TEAM_ABBREVIATION", stat]].to_dict("records")