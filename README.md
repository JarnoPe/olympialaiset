# Olympiamitalien vertailu (FIN 🇫🇮 / SWE 🇸🇪 / NOR 🇳🇴)

Tämä Streamlit-sovellus näyttää Suomen, Ruotsin ja Norjan olympiamitalit reaaliajassa olympics.comin avoimista rajapinnoista.

## Ominaisuudet

- Vertailu kolmelle maalle: Suomi, Ruotsi, Norja
- Kisa-valinta: Milano-Cortina 2026 (talvi), Pariisi 2024 (kesä), Peking 2022 (talvi)
- Käyttää olympics.com schedules-api `medal_tally.json` -lähteitä
- "Päivitä nyt" -painike ja välimuistitettu haku
- Lähteiden validointi (HTTP-tila + sisältötyyppi)
- Lähteiden hakuloki (onnistuminen/virheet)

## Käynnistys

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
