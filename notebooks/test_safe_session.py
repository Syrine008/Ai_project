import os
from pathlib import Path
import pickle
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from safe_session import parse, Node


class SessionParserTests(unittest.TestCase):
    def test_data_containers(self):
        value = {"list": [1, 2.5, True, None], "tuple": (b"data", "text"), "set": {3, 4}}
        with TemporaryDirectory() as directory:
            path = Path(directory) / "data.pkl"
            path.write_bytes(pickle.dumps(value, protocol=4))
            self.assertEqual(parse(path), value)

    def test_saved_callbacks_are_inert(self):
        class Callback:
            def __reduce__(self):
                return os.system, ("this callback must never run",)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "callback.pkl"
            path.write_bytes(pickle.dumps(Callback(), protocol=4))
            with patch("os.system") as execute:
                result = parse(path)
                execute.assert_not_called()
            self.assertIsInstance(result, Node)
            self.assertEqual(result.kind, "REDUCE")


if __name__ == "__main__":
    unittest.main()
