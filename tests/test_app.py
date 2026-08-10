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
        self.assertEqual([button.label for button in app.button], ["Clear selection"])
        self.assertTrue(all(button.disabled for button in app.button))

        rendered_text = "\n".join(markdown.value for markdown in app.markdown)
        for expected_text in (
            "Interface prototype - data not connected",
            "Overview first",
            "Zoom and filter",
            "Details on demand",
            "Crash hotspot map",
            "Crash timing",
            "Crash demand and responder locations",
            "Alcohol-related crash concentration",
            "Injury distribution by vehicle age",
            "Planned interaction:",
            "No visualization is rendered",
        ):
            with self.subTest(expected_text=expected_text):
                self.assertIn(expected_text, rendered_text)


if __name__ == "__main__":
    unittest.main()
