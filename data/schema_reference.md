## Data Schema Reference

The following Parquet files are available for analysis:

### ball_events
- **Rows**: 278,205
- **Columns**: 40

| Column | Type | Sample Values |
|--------|------|---------------|
| `event_id` | int64 | 1, 2, 3, 4, 5... (269 unique) |
| `match_id` | object | 1082591, 1082592, 1082593, 1082594, 1082595... (1169 unique) |
| `innings` | int64 | 1, 2, 3, 4, 5... (6 unique) |
| `batting_team` | object | Sunrisers Hyderabad, Royal Challengers Bengaluru, Mumbai ... |
| `batting_team_id` | object | srh, rcb, mi, rps, gl... (15 unique) |
| `bowling_team` | object | Royal Challengers Bengaluru, Sunrisers Hyderabad, Rising ... |
| `bowling_team_id` | object | rcb, srh, rps, mi, kkr... (15 unique) |
| `over_num` | int64 | 0, 1, 2, 3, 4... (20 unique) |
| `ball_num` | int64 | 1, 2, 3, 4, 5... (11 unique) |
| `ball_id` | object | 1082591_1_0.1, 1082591_1_0.2, 1082591_1_0.3, 1082591_1_0.... |
| `batter` | object | DA Warner, S Dhawan, MC Henriques, Yuvraj Singh, DJ Hooda... |
| `bowler` | object | TS Mills, A Choudhary, YS Chahal, S Aravind, SR Watson...... |
| `non_striker` | object | S Dhawan, DA Warner, MC Henriques, Yuvraj Singh, DJ Hooda... |
| `runs_off_bat` | int64 | 0, 4, 1, 6, 3... (7 unique) |
| `runs_extras` | int64 | 0, 2, 1, 4, 5... (7 unique) |
| `runs_total` | int64 | 0, 4, 2, 1, 6... (8 unique) |
| `runs_conceded` | int64 | 0, 4, 2, 1, 6... (8 unique) |
| `runs_wide` | int64 | 0, 2, 1, 5, 3... (6 unique) |
| `runs_noball` | int64 | 0, 1, 2, 5, 3 |
| `runs_bye` | int64 | 0, 1, 4, 2, 3 |
| `runs_legbye` | int64 | 0, 1, 2, 5, 3... (6 unique) |
| `runs_penalty` | int64 | 0, 5 |
| `extra_type` | object | wide, legbye, noball, bye, penalty |
| `wicket_type` | object | caught, bowled, run out, lbw, caught and bowled... (10 un... |
| `player_out` | object | DA Warner, S Dhawan, MC Henriques, Yuvraj Singh, Mandeep ... |
| `fielder` | object | Mandeep Singh, Sachin Baby, DA Warner, BCJ Cutting, Yuvra... |
| `is_wicket` | bool | False, True |
| `is_bowler_wicket` | bool | False, True |
| `is_batter_out` | bool | False, True |
| `phase` | object | powerplay, middle, death |
| `is_legal` | bool | True, False |
| `is_dot` | bool | True, False |
| `is_boundary` | bool | False, True |
| `is_four` | bool | False, True |
| `is_six` | bool | False, True |
| `target_runs` | float64 | 208.0, 185.0, 184.0, 164.0, 158.0... (175 unique) |
| `runs_batter` | int64 | 0, 4, 1, 6, 3... (7 unique) |
| `batter_id` | object | dcce6f09, 0a476045, 32198ae0, 1c914163, 73ad96ed... (702 ... |
| `bowler_id` | object | 245c97cb, 18e6906e, 57ee1fde, 957532de, 4329fbb5... (548 ... |
| `non_striker_id` | object | 0a476045, dcce6f09, 32198ae0, 1c914163, 73ad96ed... (691 ... |

### matches
- **Rows**: 1,169
- **Columns**: 21

| Column | Type | Sample Values |
|--------|------|---------------|
| `match_id` | object | 1082591, 1082592, 1082593, 1082594, 1082595... (1169 unique) |
| `match_date` | datetime64[ns] | 2017-04-05 00:00:00, 2017-04-06 00:00:00, 2017-04-07 00:0... |
| `season` | object | IPL 2017, IPL 2018, IPL 2019, IPL 2020, IPL 2021... (18 u... |
| `venue` | object | Rajiv Gandhi International Stadium, Uppal, Maharashtra Cr... |
| `city` | object | Hyderabad, Pune, Rajkot, Indore, Bengaluru... (37 unique) |
| `team1` | object | Sunrisers Hyderabad, Rising Pune Supergiant, Gujarat Lion... |
| `team2` | object | Royal Challengers Bengaluru, Mumbai Indians, Kolkata Knig... |
| `team1_id` | object | srh, rps, gl, pbks, rcb... (15 unique) |
| `team2_id` | object | rcb, mi, kkr, rps, dc... (15 unique) |
| `toss_winner` | object | Royal Challengers Bengaluru, Rising Pune Supergiant, Kolk... |
| `toss_winner_id` | object | rcb, rps, kkr, pbks, srh... (15 unique) |
| `toss_decision` | object | field, bat |
| `outcome_winner` | object | Sunrisers Hyderabad, Rising Pune Supergiant, Kolkata Knig... |
| `outcome_winner_id` | object | srh, rps, kkr, pbks, rcb... (15 unique) |
| `outcome_margin_runs` | float64 | 35.0, 15.0, 97.0, 17.0, 51.0... (101 unique) |
| `outcome_margin_wickets` | float64 | 7.0, 10.0, 6.0, 9.0, 4.0... (10 unique) |
| `player_of_match` | object | Yuvraj Singh, SPD Smith, CA Lynn, GJ Maxwell, KM Jadhav..... |
| `match_number` | float64 | 1.0, 2.0, 3.0, 4.0, 5.0... (72 unique) |
| `overs` | int64 | 20 |
| `venue_id` | object | venue_81394, venue_73492, venue_16304, venue_31580, venue... |
| `season_id` | object | ipl_2017, ipl_2018, ipl_2019, ipl_2020, ipl_2021... (18 u... |

### players
- **Rows**: 772
- **Columns**: 4

| Column | Type | Sample Values |
|--------|------|---------------|
| `player_id` | object | 1c2a64cd, 872b03f7, 99b202b3, e249fdaa, 18e6906e... (770 ... |
| `full_name` | object | A Ashish Reddy, A Badoni, A Chandila, A Chopra, A Choudha... |
| `short_name` | object | A Ashish Reddy, A Badoni, A Chandila, A Chopra, A Choudha... |
| `registry_id` | object | 1c2a64cd, 872b03f7, 99b202b3, e249fdaa, 18e6906e... (770 ... |

### teams
- **Rows**: 15
- **Columns**: 3

| Column | Type | Sample Values |
|--------|------|---------------|
| `team_id` | object | csk, dch, dc, gl, gt... (15 unique) |
| `team_name` | object | Chennai Super Kings, Deccan Chargers, Delhi Capitals, Guj... |
| `abbreviation` | object | CSK, DCH, DC, GL, GT... (15 unique) |

### venues
- **Rows**: 63
- **Columns**: 3

| Column | Type | Sample Values |
|--------|------|---------------|
| `venue_id` | object | venue_18559, venue_18917, venue_99002, venue_34060, venue... |
| `venue_name` | object | Arun Jaitley Stadium, Arun Jaitley Stadium, Delhi, Baraba... |
| `city` | object | Delhi, Cuttack, Guwahati, Lucknow, Mumbai... (37 unique) |

### seasons
- **Rows**: 18
- **Columns**: 3

| Column | Type | Sample Values |
|--------|------|---------------|
| `season_id` | object | ipl_2008, ipl_2009, ipl_2010, ipl_2011, ipl_2012... (18 u... |
| `season_name` | object | IPL 2008, IPL 2009, IPL 2010, IPL 2011, IPL 2012... (18 u... |
| `year` | int64 | 2008, 2009, 2010, 2011, 2012... (18 unique) |

## Table Relationships

- `ball_events.match_id` → `matches.match_id`
- `ball_events.batter_id` → `players.player_id`
- `ball_events.bowler_id` → `players.player_id`
- `ball_events.batting_team_id` → `teams.team_id`
- `ball_events.bowling_team_id` → `teams.team_id`
- `matches.venue_id` → `venues.venue_id`
- `matches.season_id` → `seasons.season_id`
- `matches.team1_id` → `teams.team_id`
- `matches.team2_id` → `teams.team_id`

## Key Computed Columns in ball_events

| Column | Description |
|--------|-------------|
| `phase` | Match phase: "powerplay" (overs 0-5), "middle" (6-14), "death" (15-19) |
| `is_legal` | True if ball counts toward over (not wide/noball) |
| `is_dot` | True if no runs scored on legal delivery |
| `is_boundary` | True if batter scored 4 or 6 |
| `is_four` | True if batter scored 4 |
| `is_six` | True if batter scored 6 |
| `is_wicket` | True if wicket fell on this delivery |
