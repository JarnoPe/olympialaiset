from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Olympiamitalit", page_icon="🥇", layout="wide")

TARGET_COUNTRIES = {
    "FIN": "Suomi",
    "SWE": "Ruotsi",
    "NOR": "Norja",
}

# Huom: OG2026/OG2024-tyyppiset polut eivät ole luotettavia kaikille kisoille.
# Käytetään ensisijaisesti olympics.comin schedules-api -rajapintaa, joka tarjoaa medal_tally.json-päätepisteen.
GAMES_SOURCES: dict[str, list[str]] = {
    "Milano-Cortina 2026 (talvi)": [
        "https://sph-s-api.olympics.com/winter/schedules/api/ENG/medal_tally.json",
    ],
    "Pariisi 2024 (kesä)": [
        "https://sph-s-api.olympics.com/summer/schedules/api/ENG/medal_tally.json",
    ],
    "Peking 2022 (talvi)": [
        "https://sph-s-api.olympics.com/winter/schedules/api/ENG/medal_tally.json",
    ],
}


@st.cache_data(ttl=45, show_spinner=False)
def fetch_medal_data(game_name: str) -> tuple[pd.DataFrame, str, pd.DataFrame]:
    headers = {"User-Agent": "olympialaiset-medal-dashboard/1.3"}
    source_results: list[dict[str, str | int]] = []

    for url in GAMES_SOURCES[game_name]:
        try:
            response = requests.get(url, headers=headers, timeout=12)
            response.raise_for_status()
            payload = response.json()
            rows = parse_medal_payload(payload)
            if not rows.empty:
                source_results.append({"Lähde": url, "Tila": "OK", "Rivejä": len(rows), "Virhe": ""})
                return rows, url, pd.DataFrame(source_results)

            source_results.append(
                {
                    "Lähde": url,
                    "Tila": "Tyhjä data",
                    "Rivejä": 0,
                    "Virhe": "FIN/SWE/NOR ei löytynyt payloadista",
                }
            )
        except requests.RequestException as error:
            source_results.append({"Lähde": url, "Tila": "Virhe", "Rivejä": 0, "Virhe": str(error)})
        except ValueError as error:
            source_results.append({"Lähde": url, "Tila": "Virhe", "Rivejä": 0, "Virhe": f"JSON-virhe: {error}"})

    raise RuntimeError(
        "Datan haku epäonnistui kaikista valitun olympiakisan lähteistä. "
        "Avaa 'Lähteiden validointi' nähdäksesi tarkat virheet."
    )


@st.cache_data(ttl=300, show_spinner=False)
def validate_sources(game_name: str) -> pd.DataFrame:
    headers = {"User-Agent": "olympialaiset-medal-dashboard/1.3"}
    checks: list[dict[str, str | int]] = []

    for url in GAMES_SOURCES[game_name]:
        try:
            response = requests.get(url, headers=headers, timeout=12)
            status = response.status_code
            content_type = response.headers.get("content-type", "")
            checks.append(
                {
                    "Lähde": url,
                    "HTTP": status,
                    "Sisältötyyppi": content_type,
                    "Tila": "OK" if status < 400 else "Virhe",
                    "Huomio": "",
                }
            )
        except requests.RequestException as error:
            checks.append(
                {
                    "Lähde": url,
                    "HTTP": 0,
                    "Sisältötyyppi": "",
                    "Tila": "Virhe",
                    "Huomio": str(error),
                }
            )

    return pd.DataFrame(checks)


def parse_medal_payload(payload: dict | list) -> pd.DataFrame:
    candidates: list[dict] = []

    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        for key in ("medalTable", "countries", "items", "NOC", "medals", "data"):
            if isinstance(payload.get(key), list):
                candidates = payload[key]
                break

    parsed_rows = []
    for entry in candidates:
        if not isinstance(entry, dict):
            continue

        code = (
            entry.get("countryCode")
            or entry.get("nocCode")
            or entry.get("noc")
            or entry.get("code")
            or entry.get("organisation")
        )

        if code not in TARGET_COUNTRIES:
            continue

        gold = to_int(entry.get("gold") or entry.get("goldMedals") or entry.get("g"))
        silver = to_int(entry.get("silver") or entry.get("silverMedals") or entry.get("s"))
        bronze = to_int(entry.get("bronze") or entry.get("bronzeMedals") or entry.get("b"))
        total = to_int(entry.get("total") or entry.get("totalMedals"))

        if total == 0:
            total = gold + silver + bronze

        parsed_rows.append(
            {
                "Maa": TARGET_COUNTRIES[code],
                "NOC": code,
                "Kulta": gold,
                "Hopea": silver,
                "Pronssi": bronze,
                "Yhteensä": total,
            }
        )

    frame = pd.DataFrame(parsed_rows)
    if frame.empty:
        return frame

    return frame.sort_values(by=["Kulta", "Hopea", "Pronssi"], ascending=False).reset_index(drop=True)


def to_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def format_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M:%S UTC")


st.title("🥇 Olympiamitalit reaaliajassa")
st.caption("Suomen, Ruotsin ja Norjan mitalivertailu olympics.com-lähteistä.")

selected_games = st.selectbox("Valitse olympiakisat", list(GAMES_SOURCES.keys()), index=0)

col_actions, col_updated = st.columns([1, 2])
if col_actions.button("Päivitä nyt"):
    st.cache_data.clear()
col_updated.caption(f"Sivu renderöity: {format_timestamp()}")

with st.expander("Lähteiden validointi"):
    st.dataframe(validate_sources(selected_games), use_container_width=True, hide_index=True)

try:
    medals, source_url, source_log = fetch_medal_data(selected_games)

    metric_cols = st.columns(3)
    for col, noc in zip(metric_cols, ("FIN", "SWE", "NOR")):
        country_row = medals[medals["NOC"] == noc]
        total_medals = int(country_row["Yhteensä"].iloc[0]) if not country_row.empty else 0
        col.metric(TARGET_COUNTRIES[noc], f"{total_medals} mitalia")

    medals_to_show = medals[["Maa", "Kulta", "Hopea", "Pronssi", "Yhteensä"]].copy()
    medals_to_show.index = medals_to_show.index + 1

    st.dataframe(medals_to_show, use_container_width=True)
    st.caption(f"Käytetty lähde: {source_url}")

    with st.expander("Lähteiden hakuloki"):
        st.dataframe(source_log, use_container_width=True, hide_index=True)
except Exception as error:  # noqa: BLE001
    st.error(str(error))
    st.info(
        "Jos datalähde ei avaudu, syynä on usein verkon/proxyn esto olympics.com-osoitteisiin. "
        "Tarkista ensin 'Lähteiden validointi'."
    )
