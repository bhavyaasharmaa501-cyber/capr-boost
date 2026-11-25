import os

ARTIFACTS_DIR = os.environ.get("CAPR_ARTIFACTS_DIR",
                               os.path.join(os.path.dirname(__file__), "..", "artifacts"))
DEFAULT_THRESHOLD = float(os.environ.get("CAPR_THRESHOLD", "0.5"))
API_KEY = os.environ.get("ML_SERVICE_API_KEY", "")
MAX_BATCH_FLOWS = int(os.environ.get("CAPR_MAX_BATCH_FLOWS", "20000"))
MAX_PCAP_FLOWS = int(os.environ.get("CAPR_MAX_PCAP_FLOWS", "5000"))
