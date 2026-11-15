import unittest
from datetime import datetime, timedelta, timezone

from api.tideaware.live_scenes import SceneCompatibilityError, filter_scene_records, select_scene_roles, validate_scene_group


def scene(index: int, track: str = "047", frame: str = "083", direction: str = "Descending") -> dict:
    timestamp = datetime(2026, 6, 1, tzinfo=timezone.utc) + timedelta(days=index * 12)
    name = f"NISAR_{track}_{frame}_{index}"
    return {
        "id": name,
        "properties": {
            "fileName": name,
            "startTime": timestamp.isoformat().replace("+00:00", "Z"),
            "pathNumber": track,
            "frameNumber": frame,
            "flightDirection": direction,
            "conceptID": "C3622241360-ASF",
        },
        "geometry": {"type": "Polygon", "coordinates": [[[106.7, 10.3], [107.1, 10.3], [107.1, 10.7], [106.7, 10.7], [106.7, 10.3]]]},
    }


class LiveSceneTests(unittest.TestCase):
    def test_selects_four_reference_and_two_monitoring_in_time_order(self):
        roles = select_scene_roles([scene(i) for i in range(6)], track="047", frame="083")
        self.assertEqual([item.role for item in roles], ["Reference_1", "Reference_2", "Reference_3", "Reference_4", "Monitoring_1", "Monitoring_2"])
        self.assertEqual(roles[0].scene_id, "NISAR_047_083_0")
        self.assertTrue(all(item.tide_covered is False for item in roles))

    def test_rejects_mixed_track_or_frame(self):
        with self.assertRaises(SceneCompatibilityError):
            validate_scene_group([scene(i) for i in range(5)] + [scene(5, frame="084")])

    def test_rejects_insufficient_scenes(self):
        with self.assertRaises(SceneCompatibilityError):
            select_scene_roles([scene(i) for i in range(5)], track="047", frame="083")

    def test_filters_catalog_to_one_collection_before_grouping(self):
        mixed = [scene(i) for i in range(4)]
        other = scene(4)
        other["properties"]["conceptID"] = "C2854338529-ASF"
        filtered = filter_scene_records(mixed + [other], "C3622241360-ASF")
        self.assertEqual(len(filtered), 4)
        self.assertEqual({item["properties"]["conceptID"] for item in filtered}, {"C3622241360-ASF"})


if __name__ == "__main__":
    unittest.main()
