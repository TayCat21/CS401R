"""Preliminary analysis of NWS Weather Forecast Office (WFO) social media accounts.

Inputs (all in this folder):
  Track B_ Data Collection - Sheet1.csv        official accounts (hand-collected)
  bluesky_data/nws_bluesky_handles.csv         unofficial Bluesky bot handles  (github.com/TayCat21/CS401R)
  bluesky_data/bluesky_profiles.xlsx           Bluesky profile snapshot, 2026-10-14
  bluesky_data/bluesky_posts_coded.xlsx        Bluesky posts 2026-09-11 .. 2026-11-09, coded

Outputs: output/tables/*.csv, output/figures/*.png, output/numbers.txt
Run:  python analysis.py
"""
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
TAB, FIG = OUT / "tables", OUT / "figures"
TAB.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

LOG = []
def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)

# ---------------------------------------------------------------- helpers
def spearman(a, b):
    """Spearman rank correlation without scipy (pairwise complete)."""
    m = a.notna() & b.notna()
    return a[m].rank().corr(b[m].rank())


def num(v):
    """'125k' -> 125000, '1.27k' -> 1270, '6,627' -> 6627, 'N/A'/'' -> NaN."""
    if pd.isna(v):
        return np.nan
    s = str(v).strip().lower().replace(",", "")
    if s in {"", "n/a", "na", "none", "-"} or s.startswith("n/a"):
        return np.nan
    m = re.fullmatch(r"([\d.]+)\s*([km]?)", s)
    if not m:
        return np.nan
    return float(m.group(1)) * {"": 1, "k": 1e3, "m": 1e6}[m.group(2)]

# NWS administrative region by state/territory (derived field, used for RQ2 homophily)
REGION = {}
for st in ["Arizona", "California", "Idaho", "Montana", "Nevada", "Oregon", "Utah", "Washington"]:
    REGION[st] = "Western"
for st in ["Colorado", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Michigan", "Minnesota",
           "Missouri", "Nebraska", "North Dakota", "South Dakota", "Wisconsin", "Wyoming"]:
    REGION[st] = "Central"
for st in ["Maine", "Massachusetts", "New Jersey", "New York", "North Carolina", "Ohio", "Pennsylvania",
           "South Carolina", "Vermont", "Virginia", "West Virginia"]:
    REGION[st] = "Eastern"
for st in ["Alabama", "Arkansas", "Florida", "Georgia", "Louisiana", "Mississippi", "New Mexico",
           "Oklahoma", "Puerto Rico", "Tennessee", "Texas"]:
    REGION[st] = "Southern"
REGION.update({"Alaska": "Alaska", "Hawaii": "Pacific", "Guam": "Pacific"})

# Facebook page name ("US National Weather Service <place>") -> WFO call sign
PLACE2WFO = {
    "Aberdeen South Dakota": "ABR", "Abilene/San Angelo Texas": "SJT", "Albany NY": "ALY",
    "Albuquerque New Mexico": "ABQ", "Amarillo Texas": "AMA", "Anchorage Alaska": "AFC",
    "Austin-San Antonio Texas": "EWX", "Baltimore/Washington": "LWX", "Billings Montana": "BYZ",
    "Binghamton NY": "BGM", "Birmingham Alabama": "BMX", "Bismarck North Dakota": "BIS",
    "Blacksburg VA": "RNK", "Boise Idaho": "BOI", "Boston MA": "BOX",
    "Brownsville/Rio Grande Valley Texas": "BRO", "Buffalo NY": "BUF", "Burlington VT": "BTV",
    "Caribou ME": "CAR", "Central Illinois": "ILX", "Charleston SC": "CHS", "Charleston WV": "RLX",
    "Cheyenne Wyoming": "CYS", "Chicago Illinois": "LOT", "Cleveland OH": "CLE",
    "Columbia South Carolina": "CAE", "Corpus Christi Texas": "CRP", "Denver/Boulder Colorado": "BOU",
    "Des Moines Iowa": "DMX", "Detroit / Pontiac Michigan": "DTX", "Dodge City Kansas": "DDC",
    "Duluth Minnesota": "DLH", "El Paso Texas": "EPZ", "Elko NV": "LKN", "Eureka California": "EKA",
    "Fairbanks Alaska": "AFG", "Flagstaff Arizona": "FGZ", "Fort Worth Texas": "FWD",
    "Gaylord Michigan": "APX", "Glasgow Montana": "GGW", "Goodland Kansas": "GLD",
    "Grand Forks North Dakota": "FGF", "Grand Junction Colorado": "GJT", "Grand Rapids Michigan": "GRR",
    "Gray ME": "GYX", "Great Falls Montana": "TFX", "Green Bay Wisconsin": "GRB",
    "Greenville-Spartanburg SC": "GSP", "Guam": "GUM", "Hanford California": "HNX",
    "Hastings Nebraska": "GID", "Honolulu": "HFO", "Houston-Galveston Texas": "HGX",
    "Huntsville Alabama": "HUN", "Indianapolis Indiana": "IND", "Jackson Kentucky": "JKL",
    "Jackson Mississippi": "JAN", "Jacksonville Florida": "JAX", "Juneau Alaska": "AJK",
    "Kansas City Missouri": "EAX", "Key West Florida": "KEY", "La Crosse Wisconsin": "ARX",
    "Lake Charles Louisiana": "LCH", "Las Vegas Nevada": "VEF", "Little Rock Arkansas": "LZK",
    "Los Angeles/Oxnard": "LOX", "Louisville Kentucky": "LMK", "Lubbock Texas": "LUB",
    "Marquette Michigan": "MQT", "Medford Oregon": "MFR", "Melbourne Florida": "MLB",
    "Memphis Tennessee": "MEG", "Miami Florida": "MFL", "Midland Texas": "MAF",
    "Milwaukee/Sullivan Wisconsin": "MKX", "Missoula Montana": "MSO", "Mobile Alabama": "MOB",
    "Morristown Tennessee": "MRX", "Nashville Tennessee": "OHX", "New Orleans Louisiana": "LIX",
    "New York NY": "OKX", "Newport/Morehead City NC": "MHX", "Norman Oklahoma": "OUN",
    "North Platte Nebraska": "LBF", "Northern Indiana": "IWX", "Omaha/Valley Nebraska": "OAX",
    "Paducah Kentucky": "PAH", "Peachtree City Georgia": "FFC", "Pendleton Oregon": "PDT",
    "Philadelphia/Mount Holly": "PHI", "Phoenix Arizona": "PSR", "Pittsburgh PA": "PBZ",
    "Pocatello Idaho": "PIH", "Portland Oregon": "PQR", "Pueblo Colorado": "PUB",
    "Quad Cities Iowa/Illinois": "DVN", "Raleigh NC": "RAH", "Rapid City South Dakota": "UNR",
    "Reno Nevada": "REV", "Riverton Wyoming": "RIW", "Sacramento California": "STO",
    "Saint Louis Missouri": "LSX", "Salt Lake City Utah": "SLC", "San Diego California": "SGX",
    "San Francisco Bay Area/Monterey California": "MTR", "San Juan Puerto Rico": "SJU",
    "Seattle Washington": "SEW", "Shreveport Louisiana": "SHV", "Sioux Falls South Dakota": "FSD",
    "Spokane Washington": "OTX", "Springfield Missouri": "SGF", "State College PA": "CTP",
    "Tallahassee Florida": "TAE", "Tampa Bay Florida": "TBW", "Topeka Kansas": "TOP",
    "Tucson Arizona": "TWC", "Tulsa Oklahoma": "TSA", "Twin Cities Minnesota": "MPX",
    "Wakefield VA": "AKQ", "Wichita Kansas": "ICT", "Wilmington NC": "ILM", "Wilmington OH": "ILN",
}

# Bluesky bot handles use airport codes for 36 offices; map them to WFO call signs
BSKY2WFO = {
    "ACV": "EKA", "ANC": "AFC", "ATL": "FFC", "BHM": "BMX", "BNA": "OHX", "BOS": "BOX", "CHI": "LOT",
    "CRW": "RLX", "DAY": "ILN", "DTW": "DTX", "ELP": "EPZ", "EYW": "KEY", "FAI": "AFG", "JNU": "AJK",
    "LAS": "VEF", "LAX": "LOX", "LIT": "LZK", "MEM": "MEG", "MIA": "MFL", "MKE": "MKX", "MSY": "LIX",
    "ORF": "AKQ", "PDX": "PQR", "PHL": "PHI", "PHX": "PSR", "PIT": "PBZ", "RDU": "RAH", "SAN": "SGX",
    "SDF": "LMK", "SEA": "SEW", "SFO": "MTR", "TLH": "TAE", "TPA": "TBW", "TUS": "TWC", "TYS": "MRX",
    "WAS": "LWX",
}

# ---------------------------------------------------------------- load official data
raw = pd.read_csv(HERE / "Track B_ Data Collection - Sheet1.csv")
c = raw.columns
o = pd.DataFrame({
    "wfo": raw[c[0]].str.strip(),
    "state": raw[c[1]].str.strip(),
    "fb_followers": raw[c[2]].map(num),
    "fb_following": raw[c[3]].map(num),
    "fb_wfo_follows_reported": raw[c[4]].map(num),
    "fb_wfo_follow_names": raw[c[5]],
    "fb_posts_sep14_oct14": raw[c[6]].map(num),
    "x_followers": raw[c[7]].map(num),
    "x_following": raw[c[8]].map(num),
    "bsky_official_followers": raw[c[9]].map(num),
    "ig_followers": raw[c[11]].map(num),
    "ig_following": raw[c[12]].map(num),
    "yt_subscribers": raw[c[13]].map(num),
})
o["region"] = o.state.map(REGION)
assert o.region.notna().all(), o[o.region.isna()]
N = len(o)
say(f"Official CSV: {N} WFO rows, {o.wfo.nunique()} unique call signs, {o.state.nunique()} states/territories")

# ---------------------------------------------------------------- load Bluesky (unofficial bot) data
BD = HERE / "bluesky_data"
handles = pd.read_csv(BD / "nws_bluesky_handles.csv")
prof = pd.read_excel(BD / "bluesky_profiles.xlsx")
posts = pd.read_excel(BD / "bluesky_posts_coded.xlsx", sheet_name="coded_posts",
                      usecols=["account", "post_id", "post_time", "station", "message_type",
                               "broad_group", "is_followup_part", "likes", "reposts", "replies"])
prof["code"] = prof.handle.str.split(".").str[0].str.upper()
prof["wfo"] = prof.code.map(lambda s: BSKY2WFO.get(s, s))
posts["wfo"] = posts.station.map(lambda s: BSKY2WFO.get(s, s))
posts["t"] = pd.to_datetime(posts.post_time, utc=True)
assert set(prof.wfo) == set(o.wfo), "Bluesky profiles do not map 1:1 onto CSV WFOs"
say(f"Bluesky: {len(handles)} handles, {len(prof)} profiles (snapshot {prof.collected_at.iloc[0][:10]}), "
    f"{posts.post_id.nunique():,} unique posts from {posts.wfo.nunique()} accounts, "
    f"{posts.t.min():%Y-%m-%d} to {posts.t.max():%Y-%m-%d}")
say(f"  profiles labelled 'unofficial' in display name: {prof.display_name.str.lower().str.contains('unofficial').sum()}/{len(prof)}")

# Bluesky activity window: every account is fully covered from 2026-09-30 (latest first post is
# 2026-09-29), so use 2026-10-01..2026-10-31 UTC (31 days, same length as the Facebook window).
W0, W1 = pd.Timestamp("2026-10-01", tz="UTC"), pd.Timestamp("2026-11-01", tz="UTC")
say(f"  latest first-collected post across accounts: {posts.groupby('wfo').t.min().max():%Y-%m-%d %H:%M} UTC")
win = posts[(posts.t >= W0) & (posts.t < W1)]
bs_win = win.groupby("wfo").size().rename("bsky_posts_oct")
bs = prof.set_index("wfo")[["followers", "following", "posts_count"]].rename(
    columns={"followers": "bsky_bot_followers", "following": "bsky_bot_following",
             "posts_count": "bsky_bot_posts_lifetime"})
d = o.set_index("wfo").join(bs).join(bs_win)
d["bsky_posts_oct"] = d.bsky_posts_oct.fillna(0)

# ---------------------------------------------------------------- RQ1: presence, audience, activity
plat = [("Facebook", "fb_followers"), ("X (Twitter)", "x_followers"), ("YouTube", "yt_subscribers"),
        ("Instagram", "ig_followers"), ("Bluesky - official", "bsky_official_followers"),
        ("Bluesky - unofficial bot", "bsky_bot_followers")]
rows = []
for name, col in plat:
    s = d[col].dropna()
    rows.append({"Platform": name, "WFOs with account": len(s), "% of 122 WFOs": round(100 * len(s) / N, 1),
                 "Total followers": int(s.sum()) if len(s) else 0,
                 "Median": int(s.median()) if len(s) else None, "Mean": int(round(s.mean())) if len(s) else None,
                 "Min": int(s.min()) if len(s) else None, "Max": int(s.max()) if len(s) else None})
t1 = pd.DataFrame(rows)
t1.to_csv(TAB / "table1_platform_presence_audience.csv", index=False)
say("\nTABLE 1 - platform presence & audience\n" + t1.to_string(index=False))
for name, col in plat:
    s = d[col].dropna()
    if len(s):
        top = s.idxmax()
        say(f"  largest {name}: {top} ({int(s.max()):,})")

# Platform count per WFO (official platforms only)
off_cols = ["fb_followers", "x_followers", "yt_subscribers", "ig_followers", "bsky_official_followers"]
d["n_official_platforms"] = d[off_cols].notna().sum(axis=1)
pc = d.n_official_platforms.value_counts().sort_index()
say("\nWFOs by number of official platforms: " + ", ".join(f"{k} platforms: {v}" for k, v in pc.items()))
combo = d[off_cols].notna().apply(lambda r: " + ".join(
    n for n, c_ in zip(["FB", "X", "YT", "IG", "BskyOff"], off_cols) if r[c_]), axis=1).value_counts()
say("Platform combinations:\n" + combo.to_string())
combo.rename_axis("Official platform combination").rename("WFOs").to_csv(TAB / "table_platform_combinations.csv")

# Activity
fb = d.fb_posts_sep14_oct14.dropna()
say(f"\nFacebook posts, Sept 14 - Oct 14 (31 days): n={len(fb)} WFOs with a count, total={int(fb.sum()):,}, "
    f"median={fb.median():.0f}, mean={fb.mean():.1f}, min={fb.min():.0f} ({fb.idxmin()}), "
    f"max={fb.max():.0f} ({fb.idxmax()}); median per day={fb.median()/31:.2f}")
missing_fb = d.index[d.fb_posts_sep14_oct14.isna()].tolist()
say(f"  WFOs missing a post count: {missing_fb}")
bw = d.bsky_posts_oct
say(f"Bluesky bot posts, Oct 1 - Oct 31 (31 days): total={int(bw.sum()):,}, median={bw.median():.0f}, "
    f"mean={bw.mean():.1f}, min={bw.min():.0f} ({bw.idxmin()}), max={bw.max():.0f} ({bw.idxmax()}); "
    f"median per day={bw.median()/31:.1f}")
say(f"  multi-part follow-up posts in window: {int(win.is_followup_part.sum()):,}")
lt = d.bsky_bot_posts_lifetime
say(f"Bluesky bot lifetime posts (profile count, Oct 14): total={int(lt.sum()):,}, median={lt.median():.0f}")
eng = win[["likes", "reposts", "replies"]].sum()
say(f"Bluesky engagement in Oct window: likes={int(eng.likes):,}, reposts={int(eng.reposts):,}, "
    f"replies={int(eng.replies):,}; posts with >=1 like: {(win.likes > 0).mean()*100:.1f}%")

t2 = pd.DataFrame([
    {"Measure": "Facebook posts per WFO (Sept 14 - Oct 14, 2026)", "WFOs": len(fb), "Total": int(fb.sum()),
     "Median": fb.median(), "Mean": round(fb.mean(), 1), "Min": fb.min(), "Max": fb.max(),
     "Median per day": round(fb.median() / 31, 2)},
    {"Measure": "Bluesky bot posts per WFO (Oct 1 - Oct 31, 2026)", "WFOs": len(bw), "Total": int(bw.sum()),
     "Median": bw.median(), "Mean": round(bw.mean(), 1), "Min": bw.min(), "Max": bw.max(),
     "Median per day": round(bw.median() / 31, 2)},
])
t2.to_csv(TAB / "table2_activity.csv", index=False)
say("\nTABLE 2 - activity\n" + t2.to_string(index=False))

mt = win.message_type.value_counts().rename("Posts").to_frame()
mt["Share %"] = (100 * mt.Posts / mt.Posts.sum()).round(1)
mt.to_csv(TAB / "table3_bluesky_message_types_oct.csv")
say("\nTABLE 3 - Bluesky bot message types, Oct 1-31\n" + mt.to_string())

# ---------------------------------------------------------------- RQ2: WFO-to-WFO following (Facebook)
def parse_names(cell):
    if pd.isna(cell):
        return None
    parts = [p.strip().rstrip(".").replace("Pasted text", "").strip() for p in re.split(r"[,;\n]", str(cell))]
    return [p for p in parts if p]

edges, other_nws, hidden = [], {}, []
pref = "US National Weather Service "
for wfo, cell in d.fb_wfo_follow_names.items():
    names = parse_names(cell)
    if names is None:
        continue
    if any("hidden" in n.lower() for n in names):
        hidden.append(wfo)
        continue
    for n in names:
        place = n[len(pref):].strip() if n.startswith(pref) else None
        tgt = PLACE2WFO.get(place)
        if tgt and tgt != wfo:
            edges.append((wfo, tgt))
        else:
            other_nws[n] = other_nws.get(n, 0) + 1
edges = sorted(set(edges))
E = pd.DataFrame(edges, columns=["src", "dst"])
E.to_csv(TAB / "facebook_wfo_follow_edges.csv", index=False)
observed = [w for w in d.index if w not in hidden]
say(f"\nRQ2 (Facebook following): WFOs with visible following lists={len(observed)}, hidden={len(hidden)} {hidden}")
say(f"  WFO->WFO follow ties={len(E)} ; non-WFO NWS/NOAA pages followed (mentions)={sum(other_nws.values())}")
outdeg = E.groupby("src").size().reindex(observed, fill_value=0)
indeg = E.groupby("dst").size().reindex(d.index, fill_value=0)
say(f"  out-degree (WFOs followed): median={outdeg.median():.0f}, mean={outdeg.mean():.1f}, "
    f"min={outdeg.min()}, max={outdeg.max()} ({outdeg.idxmax()}); following 0 WFOs: {(outdeg == 0).sum()}")
say(f"  in-degree (followed by n WFOs): median={indeg.median():.0f}, mean={indeg.mean():.1f}, "
    f"max={indeg.max()} ({indeg.idxmax()}); followed by none: {(indeg == 0).sum()}")
say("  top 5 most-followed: " + ", ".join(f"{k} ({v})" for k, v in indeg.sort_values(ascending=False).head(5).items()))
rep = d.fb_wfo_follows_reported.reindex(observed)
say(f"  check: parsed out-degree equals CSV '# of WFOs this account follows' for "
    f"{(rep == outdeg).sum()}/{len(observed)} WFOs (differences are non-WFO pages counted in the CSV or typos)")
dens = len(E) / (len(observed) * (N - 1))
eset = set(edges)
recip_eligible = [(a, b) for a, b in edges if b in observed]
recip = sum((b, a) in eset for a, b in recip_eligible)
say(f"  density={dens:.3f} ; reciprocity={recip}/{len(recip_eligible)} ties "
    f"= {100*recip/len(recip_eligible):.1f}% returned")

reg = d.region
E["same_region"] = E.src.map(reg) == E.dst.map(reg)
E["same_state"] = E.src.map(d.state) == E.dst.map(d.state)
reg_n = reg.value_counts()
exp_same = E.src.map(lambda w: (reg_n[reg[w]] - 1) / (N - 1)).mean()
exp_state = E.src.map(lambda w: ((d.state == d.state[w]).sum() - 1) / (N - 1)).mean()
say(f"  homophily: same-region ties={E.same_region.sum()}/{len(E)} = {100*E.same_region.mean():.1f}% "
    f"(random-follow expectation {100*exp_same:.1f}%); same-state={E.same_state.sum()} = "
    f"{100*E.same_state.mean():.1f}% (expectation {100*exp_state:.1f}%)")
rr = []
for r_ in ["Western", "Central", "Southern", "Eastern", "Alaska", "Pacific"]:
    sub = E[E.src.map(reg) == r_]
    srcs = [w for w in observed if reg[w] == r_]
    rr.append({"NWS region": r_, "WFOs": int(reg_n[r_]), "WFOs w/ visible list": len(srcs),
               "Ties sent": len(sub), "Mean WFOs followed": round(len(sub) / len(srcs), 1) if srcs else None,
               "% ties to same region": round(100 * sub.same_region.mean(), 1) if len(sub) else None,
               "% expected if random": round(100 * (reg_n[r_] - 1) / (N - 1), 1)})
t4 = pd.DataFrame(rr)
t4.loc[len(t4)] = {"NWS region": "All", "WFOs": N, "WFOs w/ visible list": len(observed), "Ties sent": len(E),
                   "Mean WFOs followed": round(len(E) / len(observed), 1),
                   "% ties to same region": round(100 * E.same_region.mean(), 1),
                   "% expected if random": round(100 * exp_same, 1)}
t4.to_csv(TAB / "table4_follow_network_by_region.csv", index=False)
say("\nTABLE 4 - Facebook WFO-following by region\n" + t4.to_string(index=False))
on = pd.Series(other_nws).sort_values(ascending=False)
on.rename_axis("Non-WFO page").rename("WFOs following").to_csv(TAB / "facebook_non_wfo_pages_followed.csv")
say("  most-followed non-WFO pages: " + ", ".join(f"{k} ({v})" for k, v in on.head(5).items()))
say(f"  Bluesky bots: every bot follows exactly {int(d.bsky_bot_following.max())} account(s) "
    f"(min {int(d.bsky_bot_following.min())}) - no WFO-to-WFO ties exist on Bluesky")

# ---------------------------------------------------------------- RQ3: multi-platform comparison
pairs = [("Facebook", "fb_followers"), ("X", "x_followers"), ("YouTube", "yt_subscribers"),
         ("Instagram", "ig_followers"), ("Bluesky bot", "bsky_bot_followers")]
both = d.dropna(subset=["fb_followers", "x_followers"])
ratio = both.fb_followers / both.x_followers
say(f"\nRQ3: WFOs on both Facebook and X: {len(both)}; FB > X for {(ratio > 1).sum()}; "
    f"median FB/X ratio={ratio.median():.2f}")
rho = spearman(both.fb_followers, both.x_followers)
say(f"  Spearman rho (FB vs X followers) = {rho:.2f}")
rows = []
for name, col in pairs:
    s = d[col]
    rows.append({"Platform": name, "WFOs": int(s.notna().sum()), "Median audience": int(s.median()),
                 "Median as % of FB (same WFOs)": round(100 * (s / d.fb_followers).median(), 1),
                 "Spearman rho vs FB": round(spearman(s, d.fb_followers), 2) if name != "Facebook" else 1.0})
t5 = pd.DataFrame(rows)
t5.to_csv(TAB / "table5_cross_platform.csv", index=False)
say("\nTABLE 5 - cross-platform audience (relative to Facebook)\n" + t5.to_string(index=False))
ok = d.dropna(subset=["fb_followers", "fb_posts_sep14_oct14"])
say(f"  Spearman rho (FB followers vs FB posts) = {spearman(ok.fb_followers, ok.fb_posts_sep14_oct14):.2f}; "
    f"(FB posts vs Bluesky bot posts) = {spearman(d.fb_posts_sep14_oct14, d.bsky_posts_oct):.2f}; "
    f"(FB followers vs Bluesky bot followers) = {spearman(d.fb_followers, d.bsky_bot_followers):.2f}")
four = d.dropna(subset=["fb_followers", "x_followers", "yt_subscribers", "ig_followers"])
say(f"  WFOs on all of FB, X, YouTube and Instagram: {len(four)} -> {sorted(four.index)}")

d.drop(columns=["fb_wfo_follow_names"]).to_csv(TAB / "wfo_master_table.csv")

# ---------------------------------------------------------------- figures
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": INK2,
                     "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.spines.top": False,
                     "axes.spines.right": False})
PCOL = {"Facebook": BLUE, "X (Twitter)": ORANGE, "YouTube": AQUA, "Instagram": YELLOW,
        "Bluesky - official": MAGENTA, "Bluesky - unofficial bot": MAGENTA}

# Figure 1: presence (bars) + audience distribution (log strip/box)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1, 1.25]})
names = t1.Platform.tolist()
y = np.arange(len(names))[::-1]
a1.barh(y, t1["WFOs with account"], color=[PCOL[n] for n in names], height=0.6)
for yi, v in zip(y, t1["WFOs with account"]):
    a1.text(v + 2, yi, f"{v}", va="center", color=INK, fontsize=9)
a1.set_yticks(y, names)
a1.set_xlim(0, 135)
a1.set_xlabel("WFOs with an account (of 122)")
a1.set_title("A. Platform presence", loc="left", color=INK, fontsize=11)
a1.xaxis.grid(True, color=GRID); a1.set_axisbelow(True)
present = [(n, c_) for n, c_ in plat if d[c_].notna().any()]
rng = np.random.default_rng(1)
for i, (n, c_) in enumerate(present[::-1]):
    s = d[c_].dropna().values
    a2.scatter(s, i + rng.uniform(-0.18, 0.18, len(s)), s=14, color=PCOL[n], alpha=0.75, linewidths=0)
    a2.plot([np.median(s)] * 2, [i - 0.3, i + 0.3], color=INK, lw=2)
    a2.text(np.median(s), i + 0.36, f"median {np.median(s):,.0f}", ha="center", fontsize=8, color=INK2)
a2.set_xscale("log")
a2.set_yticks(range(len(present)), [n for n, _ in present[::-1]])
a2.set_xlabel("Followers / subscribers per WFO (log scale)")
a2.set_title("B. Audience size per WFO account", loc="left", color=INK, fontsize=11)
a2.xaxis.grid(True, color=GRID, which="major"); a2.set_axisbelow(True)
fig.tight_layout()
fig.savefig(FIG / "fig1_platform_presence_audience.png", dpi=200)
plt.close(fig)

# Figure 2: follow network - out-degree histogram + same-region homophily
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw={"width_ratios": [1.2, 1]})
bins = np.arange(0, outdeg.max() + 2) - 0.5
a1.hist(outdeg, bins=bins, color=BLUE, edgecolor=SURF, linewidth=1)
a1.axvline(outdeg.median(), color=INK, lw=1.5, ls="--")
a1.text(outdeg.median() + 0.6, a1.get_ylim()[1] * 0.92, f"median = {outdeg.median():.0f}", color=INK, fontsize=9)
a1.set_xlabel("Number of other WFOs the office follows on Facebook")
a1.set_ylabel("WFOs")
a1.set_title(f"A. WFO-to-WFO following (n = {len(observed)} visible lists)", loc="left", color=INK, fontsize=11)
a1.yaxis.grid(True, color=GRID); a1.set_axisbelow(True)
t4r = t4[t4["Ties sent"] > 0]
yy = np.arange(len(t4r))[::-1]
a2.barh(yy + 0.18, t4r["% ties to same region"], height=0.34, color=BLUE, label="Observed")
a2.barh(yy - 0.18, t4r["% expected if random"], height=0.34, color="#b9b8b2", label="Expected if random")
for yi, v, e in zip(yy, t4r["% ties to same region"], t4r["% expected if random"]):
    a2.text(v + 1, yi + 0.18, f"{v:.0f}%", va="center", fontsize=8, color=INK)
    a2.text(e + 1, yi - 0.18, f"{e:.0f}%", va="center", fontsize=8, color=INK2)
a2.set_yticks(yy, t4r["NWS region"])
a2.set_xlim(0, 105)
a2.set_xlabel("% of follow ties pointing to a WFO in the same NWS region")
a2.set_title("B. Regional homophily", loc="left", color=INK, fontsize=11)
a2.legend(frameon=False, loc="lower right", fontsize=9)
a2.xaxis.grid(True, color=GRID); a2.set_axisbelow(True)
fig.tight_layout()
fig.savefig(FIG / "fig2_follow_network.png", dpi=200)
plt.close(fig)

# Figure 3: cross-platform audiences vs Facebook (log-log)
fig, ax = plt.subplots(figsize=(7.5, 5.4))
for name, col, colr in [("X", "x_followers", ORANGE), ("YouTube", "yt_subscribers", AQUA),
                        ("Instagram", "ig_followers", YELLOW), ("Bluesky bot", "bsky_bot_followers", MAGENTA)]:
    sub = d.dropna(subset=["fb_followers", col])
    ax.scatter(sub.fb_followers, sub[col], s=26, color=colr, alpha=0.85, edgecolors=SURF, linewidths=0.8,
               label=f"{name} (n={len(sub)})")
lim = [1e3, 2e6]
ax.plot(lim, lim, color=INK2, lw=1, ls=":")
ax.text(2.6e5, 3.4e5, "equal to Facebook", color=INK2, fontsize=8, rotation=33)
ax.annotate("GJT (1.2M FB; verify)", (d.fb_followers["GJT"], d.x_followers["GJT"]), xytext=(-20, -28),
            textcoords="offset points", ha="right", fontsize=8, color=INK2,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(8e3, 2e6); ax.set_ylim(2e1, 6e5)
ax.set_xlabel("Facebook followers (log)")
ax.set_ylabel("Followers / subscribers on other platform (log)")
ax.set_title("Audience on other platforms vs. Facebook, per WFO", loc="left", color=INK, fontsize=11)
ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.grid(True, color=GRID, which="major"); ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(FIG / "fig3_cross_platform_audience.png", dpi=200)
plt.close(fig)

(OUT / "numbers.txt").write_text("\n".join(LOG), encoding="utf-8")
say("\nwrote", OUT)
