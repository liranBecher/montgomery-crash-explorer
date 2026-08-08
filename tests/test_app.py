from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class LayoutPrototypeTest(unittest.TestCase):
    def test_app_renders_data_free_layout(self) -> None:
        app = AppTest.from_file(str(PROJECT_ROOT / "app.py")).run()

        self.assertFalse(app.exception)
        self.assertEqual(
            [tab.label for tab in app.tabs],
            [
                "Safety Hotspots",
                "First Responders",
                "Police Breathalyzers",
                "Vehicles & Injuries",
            ],
        )
        self.assertTrue(all(widget.disabled for widget in app.date_input))
        self.assertTrue(all(widget.disabled for widget in app.selectbox))


if __name__ == "__main__":
    unittest.main()
