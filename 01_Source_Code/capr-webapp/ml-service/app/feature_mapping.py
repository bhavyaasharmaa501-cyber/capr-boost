"""Maps NFStream flow fields onto the CICFlowMeter feature schema used for training."""
import numpy as np

_DIRECT = {
    "Flow Duration": "bidirectional_duration_ms",
    "Total Fwd Packet": "src2dst_packets",
    "Total Bwd packets": "dst2src_packets",
    "Total Length of Fwd Packet": "src2dst_bytes",
    "Total Length of Fwd Packets": "src2dst_bytes",
    "Total Length of Bwd Packet": "dst2src_bytes",
    "Total Length of Bwd Packets": "dst2src_bytes",
    "Fwd Packet Length Max": "src2dst_max_ps", "Fwd Packet Length Min": "src2dst_min_ps",
    "Fwd Packet Length Mean": "src2dst_mean_ps", "Fwd Packet Length Std": "src2dst_stddev_ps",
    "Bwd Packet Length Max": "dst2src_max_ps", "Bwd Packet Length Min": "dst2src_min_ps",
    "Bwd Packet Length Mean": "dst2src_mean_ps", "Bwd Packet Length Std": "dst2src_stddev_ps",
    "Flow IAT Mean": "bidirectional_mean_piat_ms", "Flow IAT Std": "bidirectional_stddev_piat_ms",
    "Flow IAT Max": "bidirectional_max_piat_ms", "Flow IAT Min": "bidirectional_min_piat_ms",
    "Fwd IAT Total": "src2dst_duration_ms", "Fwd IAT Mean": "src2dst_mean_piat_ms",
    "Fwd IAT Std": "src2dst_stddev_piat_ms", "Fwd IAT Max": "src2dst_max_piat_ms",
    "Fwd IAT Min": "src2dst_min_piat_ms",
    "Bwd IAT Total": "dst2src_duration_ms", "Bwd IAT Mean": "dst2src_mean_piat_ms",
    "Bwd IAT Std": "dst2src_stddev_piat_ms", "Bwd IAT Max": "dst2src_max_piat_ms",
    "Bwd IAT Min": "dst2src_min_piat_ms",
    "Fwd PSH Flags": "src2dst_psh_packets", "Bwd PSH Flags": "dst2src_psh_packets",
    "Fwd URG Flags": "src2dst_urg_packets", "Bwd URG Flags": "dst2src_urg_packets",
    "Packet Length Min": "bidirectional_min_ps", "Packet Length Max": "bidirectional_max_ps",
    "Packet Length Mean": "bidirectional_mean_ps", "Packet Length Std": "bidirectional_stddev_ps",
    "FIN Flag Count": "bidirectional_fin_packets", "SYN Flag Count": "bidirectional_syn_packets",
    "RST Flag Count": "bidirectional_rst_packets", "PSH Flag Count": "bidirectional_psh_packets",
    "ACK Flag Count": "bidirectional_ack_packets", "URG Flag Count": "bidirectional_urg_packets",
    "CWE Flag Count": "bidirectional_cwr_packets",
    "ECE Flag Count": "bidirectional_ece_packets",
    "Subflow Fwd Packets": "src2dst_packets", "Subflow Bwd Packets": "dst2src_packets",
    "Subflow Fwd Bytes": "src2dst_bytes", "Subflow Bwd Bytes": "dst2src_bytes",
}


def _safe_div(a, b):
    return float(a) / float(b) if b else 0.0


_COMPUTE = {
    "Flow Bytes/s": lambda r: _safe_div(r.get("bidirectional_bytes", 0), r.get("bidirectional_duration_ms", 0) / 1000.0),
    "Flow Packets/s": lambda r: _safe_div(r.get("bidirectional_packets", 0), r.get("bidirectional_duration_ms", 0) / 1000.0),
    "Fwd Packets/s": lambda r: _safe_div(r.get("src2dst_packets", 0), r.get("src2dst_duration_ms", 0) / 1000.0),
    "Bwd Packets/s": lambda r: _safe_div(r.get("dst2src_packets", 0), r.get("dst2src_duration_ms", 0) / 1000.0),
    "Packet Length Variance": lambda r: float(r.get("bidirectional_stddev_ps", 0)) ** 2,
    "Down/Up Ratio": lambda r: _safe_div(r.get("dst2src_packets", 0), r.get("src2dst_packets", 0)),
    "Average Packet Size": lambda r: _safe_div(r.get("bidirectional_bytes", 0), r.get("bidirectional_packets", 0)),
    "Fwd Segment Size Avg": lambda r: r.get("src2dst_mean_ps", 0.0),
    "Bwd Segment Size Avg": lambda r: r.get("dst2src_mean_ps", 0.0),
    "Fwd Header Length": lambda r: 32.0 * r.get("src2dst_packets", 0),
    "Bwd Header Length": lambda r: 32.0 * r.get("dst2src_packets", 0),
}

ZERO_FILLED_NOTES = (
    "Fwd Bytes/Bulk Avg, Fwd Packet/Bulk Avg, Fwd Bulk Rate Avg, Bwd Bytes/Bulk Avg, "
    "Bwd Packet/Bulk Avg, Bwd Bulk Rate Avg, FWD Init Win Bytes, Bwd Init Win Bytes, "
    "Fwd Act Data Pkts, Fwd Seg Size Min, Active Mean/Std/Max/Min, Idle Mean/Std/Max/Min"
)


def extract_features(row: dict, expected_features: list[str]) -> tuple[np.ndarray, float]:
    """Return (feature_vector, coverage) for one NFStream flow record."""
    vec = np.zeros(len(expected_features), dtype=np.float32)
    n_real = 0
    for i, name in enumerate(expected_features):
        if name in _DIRECT:
            vec[i] = float(row.get(_DIRECT[name], 0.0) or 0.0)
            n_real += 1
        elif name in _COMPUTE:
            try:
                vec[i] = float(_COMPUTE[name](row))
            except Exception:
                vec[i] = 0.0
            n_real += 1
    coverage = n_real / len(expected_features) if expected_features else 0.0
    return vec, coverage
