import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from scipy.stats import norm
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
from math_engine import calculate_parlay_probability, get_current_nba_season



ticket = []
current_analyzed_prop = None  

def add_leg_to_ticket():
    global current_analyzed_prop
    if not current_analyzed_prop:
        messagebox.showwarning("Warning", "Please run an analysis first before adding a leg.")
        return

    # Add leg to ticket
    leg = dict(current_analyzed_prop)
    ticket.append(leg)

    # 1. Calculate joint parlay probability using math_engine
    probs = [item["prob"] for item in ticket]
    combined_prob = calculate_parlay_probability(probs)

    # 2. Calculate fair multiplier (break-even payout)
    fair_multiplier = (1.0 / combined_prob) if combined_prob > 0 else 0.0

    # 3. Update GUI display
    legs_text = "\n".join([f"• {item['desc']} (Model: {item['prob']*100:.1f}%)" for item in ticket])
    lbl_ticket_legs.config(text=legs_text if legs_text else "No legs added yet.")
    lbl_parlay_prob.config(text=f"{combined_prob*100:.1f}%")
    lbl_fair_odds.config(text=f"{fair_multiplier:.2f}x")

def clear_ticket():
    global ticket, current_analyzed_prop
    ticket.clear()
    current_analyzed_prop = None
    lbl_ticket_legs.config(text="No legs added yet.")
    lbl_parlay_prob.config(text="--")
    lbl_fair_odds.config(text="--")

def analyze_prop():
    global current_analyzed_prop
    player_name = entry_player.get().strip()
    stat_choice = combo_stat.get().strip()
    target_str = entry_target.get().strip()

    if not player_name or not target_str:
        messagebox.showerror("Input Error", "Please provide a player name and a target line.")
        return

    try:
        target_line = float(target_str)
    except ValueError:
        messagebox.showerror("Input Error", "Target line must be a valid number (e.g. 24.5).")
        return

    status_label.config(text=f"Fetching data for {player_name}...", fg="#d97706")
    root.update_idletasks()

    # Query Player
    player_dict = players.find_players_by_full_name(player_name)
    if not player_dict:
        messagebox.showerror("Error", f"Player '{player_name}' not found.")
        status_label.config(text="Ready", fg="#6b7280")
        return

    player_id = player_dict[0]["id"]
    formal_name = player_dict[0]["full_name"]

    # Fetch Logs
    try:
        gamelog = playergamelog.PlayerGameLog(
            player_id=player_id, 
            season='2025-26', #remember to update season
            season_type_all_star='Regular Season'
        )
        df = gamelog.get_data_frames()[0]
    except Exception as e:
        messagebox.showerror("API Error", f"Failed to retrieve stats: {e}")
        status_label.config(text="Ready", fg="#6b7280")
        return

    if df.empty:
        messagebox.showwarning("No Data", "No game logs found for season 2025-26.")
        status_label.config(text="Ready", fg="#6b7280")
        return

   
    df = df[df["MIN"] >= 15]
    last_10 = df.head(10)

    if last_10.empty:
        messagebox.showwarning("No Data", "No games with 15+ minutes recorded.")
        status_label.config(text="Ready", fg="#6b7280")
        return

    # Metrics & Volatility Math
    avg_5 = df[stat_choice].head(5).mean()
    avg_10 = last_10[stat_choice].mean()
    std_10 = last_10[stat_choice].std()
    cv_10 = (std_10 / avg_10) if avg_10 > 0 else 0

    # Historical Hit Rate
    hits = (last_10[stat_choice] >= target_line).sum()
    hit_pct = (hits / len(last_10)) * 100

    # Normal Distribution Probability Modeling
    if std_10 > 0:
        corrected_line = target_line - 0.5
        model_prob = norm.sf(corrected_line, loc=avg_10, scale=std_10) * 100
    else:
        model_prob = 100.0 if avg_10 >= target_line else 0.0

  
    current_analyzed_prop = {
        "desc": f"{formal_name} {target_line}+ {stat_choice}",
        "prob": model_prob / 100.0
    }

 
    if cv_10 < 0.20:
        risk_text = "HIGH CONSISTENCY (Safe Floor)"
        risk_color = "#15803d"
    elif cv_10 <= 0.35:
        risk_text = "MODERATE VOLATILITY"
        risk_color = "#b45309"
    else:
        risk_text = "HIGH VOLATILITY (Boom-or-Bust)"
        risk_color = "#b91c1c"

  
    lbl_player_header.config(text=f"{formal_name} — {target_line}+ {stat_choice}")
    lbl_avg5.config(text=f"{avg_5:.1f}")
    lbl_avg10.config(text=f"{avg_10:.1f}")
    lbl_hitrate.config(text=f"{hits}/{len(last_10)} ({hit_pct:.0f}%)")
    lbl_model_prob.config(text=f"{model_prob:.1f}%")
    lbl_spread.config(text=f"±{std_10:.1f}")
    lbl_volatility.config(text=f"{cv_10:.2f} — {risk_text}", fg=risk_color)

    recent_values = [str(x) for x in last_10[stat_choice].tolist()]
    lbl_recent_vals.config(text="Recent Games (Latest -> Oldest):\n" + "  |  ".join(recent_values))

    status_label.config(text="Analysis Complete", fg="#15803d")


# ==========================================
# GUI Layout Configuration
# ==========================================
root = tk.Tk()
root.title("NBA Parlay Calculator")
root.geometry("540x760")
root.configure(bg="#f3f4f6")
root.resizable(False, False)

# Header Section
header_frame = tk.Frame(root, bg="#111827", padx=16, pady=14)
header_frame.pack(fill="x")

title_lbl = tk.Label(header_frame, text="NBA Parlay Calculator", font=("Segoe UI", 16, "bold"), fg="#ffffff", bg="#111827")
title_lbl.pack(anchor="w")

subtitle_lbl = tk.Label(header_frame, text="Best Calculator in town", font=("Segoe UI", 9), fg="#9ca3af", bg="#111827")
subtitle_lbl.pack(anchor="w")

# Input Controls Card
input_card = tk.LabelFrame(root, text=" Query Parameters ", font=("Segoe UI", 10, "bold"), bg="#ffffff", padx=14, pady=10)
input_card.pack(fill="x", padx=16, pady=10)

# Row 0: Player
tk.Label(input_card, text="Player Full Name:", font=("Segoe UI", 9), bg="#ffffff").grid(row=0, column=0, sticky="w", pady=3)
entry_player = tk.Entry(input_card, font=("Segoe UI", 10), width=24)
entry_player.insert(0, "Enter Player Name")
entry_player.grid(row=0, column=1, pady=3, padx=6)

# Row 1: Stat Category
tk.Label(input_card, text="Stat Category:", font=("Segoe UI", 9), bg="#ffffff").grid(row=1, column=0, sticky="w", pady=3)
combo_stat = ttk.Combobox(input_card, values=["PTS", "REB", "AST", "FG3M"], state="readonly", width=22)
combo_stat.set("PTS")
combo_stat.grid(row=1, column=1, pady=3, padx=6)

# Row 2: Target Line
tk.Label(input_card, text="Target Prop Line:", font=("Segoe UI", 9), bg="#ffffff").grid(row=2, column=0, sticky="w", pady=3)
entry_target = tk.Entry(input_card, font=("Segoe UI", 10), width=24)
entry_target.insert(0, "0")
entry_target.grid(row=2, column=1, pady=3, padx=6)

# Row 3: Action Buttons
btn_frame = tk.Frame(input_card, bg="#ffffff")
btn_frame.grid(row=3, column=0, columnspan=2, pady=(10, 4), sticky="ew")

btn_analyze = tk.Button(btn_frame, text="1. Run Analysis", font=("Segoe UI", 9, "bold"), bg="#2563eb", fg="#ffffff", relief="flat", cursor="hand2", padx=10, pady=4, command=analyze_prop)
btn_analyze.pack(side="left", fill="x", expand=True, padx=(0, 4))

btn_add = tk.Button(btn_frame, text="2. Add Leg to Ticket", font=("Segoe UI", 9, "bold"), bg="#15803d", fg="#ffffff", relief="flat", cursor="hand2", padx=10, pady=4, command=add_leg_to_ticket)
btn_add.pack(side="right", fill="x", expand=True, padx=(4, 0))

# Results Display Card
results_card = tk.LabelFrame(root, text=" Analytics Summary ", font=("Segoe UI", 10, "bold"), bg="#ffffff", padx=14, pady=10)
results_card.pack(fill="x", padx=16, pady=6)

lbl_player_header = tk.Label(results_card, text="No query loaded", font=("Segoe UI", 11, "bold"), fg="#1f2937", bg="#ffffff")
lbl_player_header.pack(anchor="w", pady=(0, 6))

grid_stats = tk.Frame(results_card, bg="#ffffff")
grid_stats.pack(fill="x", pady=2)

tk.Label(grid_stats, text="Last 5 Avg:", font=("Segoe UI", 9), bg="#ffffff", fg="#4b5563").grid(row=0, column=0, sticky="w", pady=2)
lbl_avg5 = tk.Label(grid_stats, text="--", font=("Segoe UI", 9, "bold"), bg="#ffffff")
lbl_avg5.grid(row=0, column=1, sticky="w", padx=10)

tk.Label(grid_stats, text="Last 10 Avg:", font=("Segoe UI", 9), bg="#ffffff", fg="#4b5563").grid(row=1, column=0, sticky="w", pady=2)
lbl_avg10 = tk.Label(grid_stats, text="--", font=("Segoe UI", 9, "bold"), bg="#ffffff")
lbl_avg10.grid(row=1, column=1, sticky="w", padx=10)

tk.Label(grid_stats, text="Hit Rate (Last 10):", font=("Segoe UI", 9), bg="#ffffff", fg="#4b5563").grid(row=2, column=0, sticky="w", pady=2)
lbl_hitrate = tk.Label(grid_stats, text="--", font=("Segoe UI", 9, "bold"), bg="#ffffff")
lbl_hitrate.grid(row=2, column=1, sticky="w", padx=10)

tk.Label(grid_stats, text="Model Probability:", font=("Segoe UI", 9), bg="#ffffff", fg="#4b5563").grid(row=3, column=0, sticky="w", pady=2)
lbl_model_prob = tk.Label(grid_stats, text="--", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#2563eb")
lbl_model_prob.grid(row=3, column=1, sticky="w", padx=10)

tk.Label(grid_stats, text="Spread (Std Dev):", font=("Segoe UI", 9), bg="#ffffff", fg="#4b5563").grid(row=4, column=0, sticky="w", pady=2)
lbl_spread = tk.Label(grid_stats, text="--", font=("Segoe UI", 9, "bold"), bg="#ffffff")
lbl_spread.grid(row=4, column=1, sticky="w", padx=10)

tk.Label(grid_stats, text="Volatility / Risk:", font=("Segoe UI", 9), bg="#ffffff", fg="#4b5563").grid(row=5, column=0, sticky="w", pady=2)
lbl_volatility = tk.Label(grid_stats, text="--", font=("Segoe UI", 9, "bold"), bg="#ffffff")
lbl_volatility.grid(row=5, column=1, sticky="w", padx=10)

lbl_recent_vals = tk.Label(results_card, text="", font=("Segoe UI", 8), bg="#ffffff", fg="#4b5563", justify="left")
lbl_recent_vals.pack(anchor="w", pady=(6, 0))

# Parlay Ticket Display Card
parlay_card = tk.LabelFrame(root, text=" Parlay Ticket Engine (Multi-Leg Hit Rate) ", font=("Segoe UI", 10, "bold"), bg="#ffffff", padx=14, pady=10)
parlay_card.pack(fill="x", padx=16, pady=6)

lbl_ticket_legs = tk.Label(parlay_card, text="No legs added yet.", font=("Segoe UI", 8), bg="#ffffff", fg="#4b5563", justify="left")
lbl_ticket_legs.pack(anchor="w", pady=(0, 4))

parlay_grid = tk.Frame(parlay_card, bg="#ffffff")
parlay_grid.pack(fill="x", pady=4)

tk.Label(parlay_grid, text="Combined Hit Chance:", font=("Segoe UI", 9), bg="#ffffff", fg="#4b5563").grid(row=0, column=0, sticky="w")
lbl_parlay_prob = tk.Label(parlay_grid, text="--", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#2563eb")
lbl_parlay_prob.grid(row=0, column=1, sticky="w", padx=10)

tk.Label(parlay_grid, text="Fair Break-Even Odds:", font=("Segoe UI", 9), bg="#ffffff", fg="#4b5563").grid(row=0, column=2, sticky="w", padx=(10, 0))
lbl_fair_odds = tk.Label(parlay_grid, text="--", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#15803d")
lbl_fair_odds.grid(row=0, column=3, sticky="w", padx=10)

btn_clear = tk.Button(parlay_card, text="Reset Ticket", font=("Segoe UI", 8), bg="#ef4444", fg="#ffffff", relief="flat", cursor="hand2", padx=6, pady=2, command=clear_ticket)
btn_clear.pack(anchor="e", pady=(4, 0))

# Bottom Status Bar
status_label = tk.Label(root, text="Ready", font=("Segoe UI", 8), bg="#f3f4f6", fg="#6b7280", anchor="w", padx=16)
status_label.pack(fill="x", side="bottom", pady=4)

root.mainloop()