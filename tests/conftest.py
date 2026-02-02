import sys
from types import ModuleType
from unittest.mock import MagicMock

# Create a fake 'consumer' package
consumer_pkg = ModuleType("consumer")

# Create fake submodules
consumer_pkg.analytics_producer = MagicMock()
consumer_pkg.influx_writer = MagicMock()
consumer_pkg.metrics = MagicMock()
consumer_pkg.schemas = MagicMock()

# Register everything in sys.modules
sys.modules["consumer"] = consumer_pkg
sys.modules["consumer.analytics_producer"] = consumer_pkg.analytics_producer
sys.modules["consumer.influx_writer"] = consumer_pkg.influx_writer
sys.modules["consumer.metrics"] = consumer_pkg.metrics
sys.modules["consumer.schemas"] = consumer_pkg.schemas