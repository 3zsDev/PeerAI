from pathlib import Path

from peerai.config import load_settings


def test_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    s = load_settings()
    assert s.dwell_ms == 700 and s.trigger_mode == "confirm"
    assert s.text.base_url.endswith("/v1")


def test_overrides_from_toml(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('dwell_ms = 650\nscreenshot_box = [800, 500]\n[ai.text]\nbase_url = "http://127.0.0.1:11435/v1"\nmodel = "deepseek-chat"\n[ai.vision]\nmodel = "llava"\n')
    s = load_settings(cfg)
    assert s.dwell_ms == 650
    assert s.screenshot_box == (800, 500)
    assert s.text.base_url == "http://127.0.0.1:11435/v1" and s.text.model == "deepseek-chat"
    assert s.vision.model == "llava"
    assert isinstance(s.calibration_path, Path)


def test_calibration_model_roundtrip(tmp_path):
    np = __import__("numpy")
    from peerai.input.calibration import GazeModel

    rng = np.random.default_rng(0)
    feats = rng.normal(size=(200, 7))
    targets = np.stack([feats[:, 0] * 500 + 960, feats[:, 1] * 300 + 540], axis=1)
    m = GazeModel.fit(feats, targets)
    x, y = m.predict(feats[0])
    assert abs(x - targets[0, 0]) < 5 and abs(y - targets[0, 1]) < 5
    m.save(tmp_path / "c.json")
    loaded = GazeModel.load(tmp_path / "c.json")
    assert loaded.predict(feats[1]) == m.predict(feats[1])
