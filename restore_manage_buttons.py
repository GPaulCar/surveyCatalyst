from pathlib import Path

ROOT = Path.cwd()
BOOT_PATH = ROOT / "app" / "static" / "ui_boot.js"

OLD_BLOCK = """    <div class="ui3Section">
      <div class="ui3SectionTitle">Surveys</div>
      <select id="surveySelect" class="ui3Select">
        <option value="">Select survey</option>
        ${state.surveys.map(s => `<option value="${s.id}" ${String(state.activeSurveyId)===String(s.id)?'selected':''}>${(s.title || s.name || ('Survey ' + s.id))}</option>`).join('')}
      </select>
      <div style="margin-top:12px;">
        <button class="ui3Btn" id="surveySetBtn" type="button">Set active</button>
        <button class="ui3Btn secondary" id="surveyRefreshBtn" type="button">Refresh surveys</button>
      </div>
    </div>"""

NEW_BLOCK = """    <div class="ui3Section">
      <div class="ui3SectionTitle">Surveys</div>
      <select id="surveySelect" class="ui3Select">
        <option value="">Select survey</option>
        ${state.surveys.map(s => `<option value="${s.id}" ${String(state.activeSurveyId)===String(s.id)?'selected':''}>${(s.title || s.name || ('Survey ' + s.id))}</option>`).join('')}
      </select>
      <div style="margin-top:12px;">
        <button class="ui3Btn" id="surveySetBtn" type="button">Set active</button>
        <button class="ui3Btn secondary" id="surveyRefreshBtn" type="button">Refresh surveys</button>
        <button class="ui3Btn secondary" id="surveyZoomBtn" type="button">Zoom to</button>
        <button class="ui3Btn secondary" id="surveyFeaturesBtn" type="button">Load features</button>
      </div>
    </div>"""

OLD_BIND = """  const refreshBtn = document.getElementById('sysRefreshBtn');
  const healthBtn = document.getElementById('sysHealthBtn');
  const surveyRefreshBtn = document.getElementById('surveyRefreshBtn');
  const surveySetBtn = document.getElementById('surveySetBtn');
  const surveySelect = document.getElementById('surveySelect');

  if (refreshBtn) refreshBtn.onclick = refreshSystem;
  if (healthBtn) healthBtn.onclick = async () => {
    try {
      const res = await fetch('/health', { cache: 'no-store' });
      setBanner(res.ok ? '127.0.0.1:8000 healthy' : 'Health check failed');
      setTimeout(() => setBanner(''), 2000);
    } catch {
      setBanner('Health check failed');
      setTimeout(() => setBanner(''), 2000);
    }
  };
  if (surveyRefreshBtn) surveyRefreshBtn.onclick = refreshSurveys;
  if (surveySetBtn) surveySetBtn.onclick = () => {
    state.activeSurveyId = surveySelect && surveySelect.value ? surveySelect.value : null;
    setBanner(state.activeSurveyId ? `Active survey set: ${state.activeSurveyId}` : '');
    setTimeout(() => setBanner(''), 2000);
  };"""

NEW_BIND = """  const refreshBtn = document.getElementById('sysRefreshBtn');
  const healthBtn = document.getElementById('sysHealthBtn');
  const surveyRefreshBtn = document.getElementById('surveyRefreshBtn');
  const surveySetBtn = document.getElementById('surveySetBtn');
  const surveyZoomBtn = document.getElementById('surveyZoomBtn');
  const surveyFeaturesBtn = document.getElementById('surveyFeaturesBtn');
  const surveySelect = document.getElementById('surveySelect');

  if (refreshBtn) refreshBtn.onclick = refreshSystem;
  if (healthBtn) healthBtn.onclick = async () => {
    try {
      const res = await fetch('/health', { cache: 'no-store' });
      setBanner(res.ok ? '127.0.0.1:8000 healthy' : 'Health check failed');
      setTimeout(() => setBanner(''), 2000);
    } catch {
      setBanner('Health check failed');
      setTimeout(() => setBanner(''), 2000);
    }
  };
  if (surveyRefreshBtn) surveyRefreshBtn.onclick = refreshSurveys;
  if (surveySetBtn) surveySetBtn.onclick = () => {
    state.activeSurveyId = surveySelect && surveySelect.value ? surveySelect.value : null;
    setBanner(state.activeSurveyId ? `Active survey set: ${state.activeSurveyId}` : '');
    setTimeout(() => setBanner(''), 2000);
  };
  if (surveyZoomBtn) surveyZoomBtn.onclick = async () => {
    const surveyId = surveySelect && surveySelect.value ? surveySelect.value : state.activeSurveyId;
    if (!surveyId) {
      setBanner('Select a survey first.');
      setTimeout(() => setBanner(''), 1500);
      return;
    }
    try {
      const geojson = await fetchJson(`/api/surveys/${surveyId}/features?limit=20000`);
      const format = new ol.format.GeoJSON();
      const features = format.readFeatures(geojson, {
        featureProjection: map.getView().getProjection()
      });
      if (!features.length) {
        setBanner('No features found for selected survey.');
        setTimeout(() => setBanner(''), 1500);
        return;
      }
      const extent = ol.extent.createEmpty();
      features.forEach(f => ol.extent.extend(extent, f.getGeometry().getExtent()));
      map.getView().fit(extent, { padding: [40, 40, 40, 40], duration: 300, maxZoom: 18 });
      setBanner(`Zoomed to survey ${surveyId}.`);
      setTimeout(() => setBanner(''), 1500);
    } catch (err) {
      setBanner(`Zoom failed: ${err.message}`);
      setTimeout(() => setBanner(''), 1500);
    }
  };
  if (surveyFeaturesBtn) surveyFeaturesBtn.onclick = async () => {
    const surveyId = surveySelect && surveySelect.value ? surveySelect.value : state.activeSurveyId;
    if (!surveyId) {
      setBanner('Select a survey first.');
      setTimeout(() => setBanner(''), 1500);
      return;
    }
    try {
      const geojson = await fetchJson(`/api/surveys/${surveyId}/features?limit=20000`);
      const count = (geojson.features || []).length;
      setBanner(`Loaded ${count} survey features.`);
      setTimeout(() => setBanner(''), 1500);
    } catch (err) {
      setBanner(`Feature load failed: ${err.message}`);
      setTimeout(() => setBanner(''), 1500);
    }
  };"""

def main() -> None:
    if not BOOT_PATH.exists():
        raise FileNotFoundError(BOOT_PATH)

    text = BOOT_PATH.read_text(encoding="utf-8")

    if OLD_BLOCK in text:
        text = text.replace(OLD_BLOCK, NEW_BLOCK, 1)

    if OLD_BIND in text:
        text = text.replace(OLD_BIND, NEW_BIND, 1)

    BOOT_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] updated {BOOT_PATH}")
    print("[DONE] survey manage buttons restored")

if __name__ == "__main__":
    main()