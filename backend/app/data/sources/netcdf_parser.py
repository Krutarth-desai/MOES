import io
import logging
import math
import struct
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger("moes.data.netcdf")

# Standard NetCDF-3 data type codes
NC_BYTE = 1
NC_CHAR = 2
NC_SHORT = 3
NC_INT = 4
NC_FLOAT = 5
NC_DOUBLE = 6

# Canonical CF conventions variable synonyms
VARIABLE_SYNONYMS = {
    "temperature": ["t2m", "temp", "temperature", "temperature_2m", "tas", "2t", "t_2m"],
    "rainfall": ["tp", "precip", "precipitation", "rainfall", "rain", "pr", "tot_prec", "rain_mm"],
    "wind_speed": ["ws10", "wind_speed", "wind_speed_10m", "si10", "sfcwind", "ws", "wspd"],
    "wind_direction": ["wdir", "wind_dir", "wind_direction", "wdir10", "wd"],
    "u_wind": ["u10", "u_wind", "10u", "u"],
    "v_wind": ["v10", "v_wind", "10v", "v"],
}

COORD_SYNONYMS = {
    "latitude": ["lat", "latitude", "lats", "y"],
    "longitude": ["lon", "longitude", "lons", "x"],
    "time": ["time", "valid_time", "timestamp", "times", "t"],
    "lead_time": ["lead_time", "step", "forecast_period", "lead_time_hours", "fhour"],
    "station": ["station", "station_id", "station_code", "stations"],
}


class NetCDFDataset:
    """
    Standard in-memory representation of a meteorological NetCDF dataset.
    Compatible across netCDF4, xarray, scipy, and pure-Python readers.
    """

    def __init__(self, filename: str = ""):
        self.filename = filename
        self.dimensions: Dict[str, int] = {}
        self.variables: Dict[str, np.ndarray] = {}
        self.attributes: Dict[str, Any] = {}
        self.var_attributes: Dict[str, Dict[str, Any]] = {}

    def get_var(self, name: str) -> Optional[np.ndarray]:
        if name in self.variables:
            return self.variables[name]
        lower_name = name.lower()
        for k, v in self.variables.items():
            if k.lower() == lower_name:
                return v
        return None

    def find_variable(self, canonical_name: str) -> Optional[Tuple[str, np.ndarray]]:
        """Finds a variable using canonical meteorological synonyms."""
        synonyms = VARIABLE_SYNONYMS.get(canonical_name, [canonical_name])
        for syn in synonyms:
            var = self.get_var(syn)
            if var is not None:
                # Retrieve actual name
                for k in self.variables.keys():
                    if k.lower() == syn.lower():
                        return k, var
        return None

    def find_coordinate(self, canonical_coord: str) -> Optional[Tuple[str, np.ndarray]]:
        """Finds a coordinate using standard synonym mappings."""
        synonyms = COORD_SYNONYMS.get(canonical_coord, [canonical_coord])
        for syn in synonyms:
            var = self.get_var(syn)
            if var is not None:
                for k in self.variables.keys():
                    if k.lower() == syn.lower():
                        return k, var
        return None


class PurePythonNetCDF3Reader:
    """
    Lightweight, dependency-free binary reader for NetCDF-3 Classic (CDF-1)
    and 64-bit Offset (CDF-2) meteorological datasets.
    """

    @classmethod
    def read(cls, path: Path) -> NetCDFDataset:
        with open(path, "rb") as f:
            data = f.read()

        ds = NetCDFDataset(str(path))
        buf = io.BytesIO(data)

        # Magic: CDF\x01 or CDF\x02
        magic = buf.read(4)
        if magic == b"CDF\x01":
            version = 1
        elif magic == b"CDF\x02":
            version = 2
        else:
            raise ValueError(f"Not a valid NetCDF-3 file (Magic bytes: {magic})")

        numrecs = struct.unpack(">i", buf.read(4))[0]

        # 1. Dim array
        tag = struct.unpack(">i", buf.read(4))[0]
        if tag == 0x0000000A:
            nelems = struct.unpack(">i", buf.read(4))[0]
            for _ in range(nelems):
                d_name = cls._read_string(buf)
                d_len = struct.unpack(">i", buf.read(4))[0]
                ds.dimensions[d_name] = d_len
        elif tag != 0:
            raise ValueError(f"Malformed dim_array tag: {tag}")

        # 2. Global att array
        tag = struct.unpack(">i", buf.read(4))[0]
        if tag == 0x0000000C:
            nelems = struct.unpack(">i", buf.read(4))[0]
            for _ in range(nelems):
                a_name, a_val = cls._read_attribute(buf)
                ds.attributes[a_name] = a_val
        elif tag != 0:
            raise ValueError(f"Malformed gatt_array tag: {tag}")

        # 3. Var array
        tag = struct.unpack(">i", buf.read(4))[0]
        var_specs = []
        if tag == 0x0000000B:
            nelems = struct.unpack(">i", buf.read(4))[0]
            for _ in range(nelems):
                v_name = cls._read_string(buf)
                v_ndims = struct.unpack(">i", buf.read(4))[0]
                v_dim_ids = [struct.unpack(">i", buf.read(4))[0] for _ in range(v_ndims)]

                # Var attributes
                v_atts = {}
                v_tag = struct.unpack(">i", buf.read(4))[0]
                if v_tag == 0x0000000C:
                    v_att_count = struct.unpack(">i", buf.read(4))[0]
                    for _ in range(v_att_count):
                        va_name, va_val = cls._read_attribute(buf)
                        v_atts[va_name] = va_val

                ds.var_attributes[v_name] = v_atts

                v_type = struct.unpack(">i", buf.read(4))[0]
                v_size = struct.unpack(">i", buf.read(4))[0]
                v_begin = struct.unpack(">q" if version == 2 else ">i", buf.read(8 if version == 2 else 4))[0]

                var_specs.append((v_name, v_dim_ids, v_type, v_size, v_begin))

        # Dim list in order
        dim_names = list(ds.dimensions.keys())

        # Read variable data
        for v_name, v_dim_ids, v_type, v_size, v_begin in var_specs:
            shape = [ds.dimensions[dim_names[did]] for did in v_dim_ids]
            count = 1
            for s in shape:
                count *= (s if s > 0 else 1)

            buf.seek(v_begin)
            dtype_map = {
                NC_BYTE: (">b", np.int8, 1),
                NC_CHAR: (">c", np.bytes_, 1),
                NC_SHORT: (">h", np.int16, 2),
                NC_INT: (">i", np.int32, 4),
                NC_FLOAT: (">f", np.float32, 4),
                NC_DOUBLE: (">d", np.float64, 8),
            }
            fmt_char, np_dtype, elem_size = dtype_map.get(v_type, (">f", np.float32, 4))
            total_bytes = count * elem_size
            raw_bytes = buf.read(total_bytes)

            try:
                arr = np.frombuffer(raw_bytes, dtype=np.dtype(np_dtype).newbyteorder(">"))
                arr = arr.astype(np_dtype, copy=False)
                if shape:
                    arr = arr.reshape(shape)
                ds.variables[v_name] = arr
            except Exception as e:
                logger.warning("Failed to unpack variable %s: %s", v_name, e)
                ds.variables[v_name] = np.zeros(shape or (1,), dtype=np_dtype)

        return ds

    @classmethod
    def _read_string(cls, buf: io.BytesIO) -> str:
        s_len = struct.unpack(">i", buf.read(4))[0]
        s_bytes = buf.read(s_len)
        padding = (4 - (s_len % 4)) % 4
        if padding:
            buf.read(padding)
        return s_bytes.decode("utf-8", errors="replace")

    @classmethod
    def _read_attribute(cls, buf: io.BytesIO) -> Tuple[str, Any]:
        a_name = cls._read_string(buf)
        a_type = struct.unpack(">i", buf.read(4))[0]
        a_len = struct.unpack(">i", buf.read(4))[0]

        if a_type == NC_CHAR:
            val_bytes = buf.read(a_len)
            pad = (4 - (a_len % 4)) % 4
            if pad:
                buf.read(pad)
            return a_name, val_bytes.decode("utf-8", errors="replace").strip("\x00")
        elif a_type == NC_FLOAT:
            vals = [struct.unpack(">f", buf.read(4))[0] for _ in range(a_len)]
            return a_name, vals[0] if len(vals) == 1 else vals
        elif a_type == NC_DOUBLE:
            vals = [struct.unpack(">d", buf.read(8))[0] for _ in range(a_len)]
            return a_name, vals[0] if len(vals) == 1 else vals
        elif a_type in (NC_INT, NC_SHORT, NC_BYTE):
            vals = [struct.unpack(">i", buf.read(4))[0] for _ in range(a_len)]
            return a_name, vals[0] if len(vals) == 1 else vals
        else:
            buf.read(a_len * 4)
            return a_name, None


def write_test_netcdf3(
    output_path: Path,
    variables: Dict[str, np.ndarray],
    dimensions: Dict[str, int],
    var_dims: Dict[str, List[str]],
    global_attrs: Optional[Dict[str, str]] = None,
    var_attrs: Optional[Dict[str, Dict[str, str]]] = None,
) -> None:
    """
    Writes a fully standard-compliant binary NetCDF-3 (CDF-1) file.
    Enables generating real binary NetCDF files for testing and verification without external C libraries.
    """
    buf = io.BytesIO()
    global_attrs = global_attrs or {}
    var_attrs = var_attrs or {}

    # Magic & Numrecs
    buf.write(b"CDF\x01")
    buf.write(struct.pack(">i", 0))

    # 1. Dim array
    dim_names = list(dimensions.keys())
    buf.write(struct.pack(">i", 0x0000000A))
    buf.write(struct.pack(">i", len(dim_names)))
    for dname in dim_names:
        _write_string(buf, dname)
        buf.write(struct.pack(">i", dimensions[dname]))

    # 2. Gatt array
    buf.write(struct.pack(">i", 0x0000000C))
    buf.write(struct.pack(">i", len(global_attrs)))
    for aname, aval in global_attrs.items():
        _write_string(buf, aname)
        buf.write(struct.pack(">i", NC_CHAR))
        _write_string(buf, str(aval))

    # 3. Var array
    var_names = list(variables.keys())
    buf.write(struct.pack(">i", 0x0000000B))
    buf.write(struct.pack(">i", len(var_names)))

    # Compute data offsets
    # We will reserve space for var headers, then calculate begin offsets
    var_header_pos = buf.tell()
    # Write placeholder var table
    for vname in var_names:
        _write_string(buf, vname)
        vdims = var_dims.get(vname, [])
        buf.write(struct.pack(">i", len(vdims)))
        for vd in vdims:
            buf.write(struct.pack(">i", dim_names.index(vd)))

        vatts = var_attrs.get(vname, {})
        buf.write(struct.pack(">i", 0x0000000C))
        buf.write(struct.pack(">i", len(vatts)))
        for vaname, vaval in vatts.items():
            _write_string(buf, vaname)
            buf.write(struct.pack(">i", NC_CHAR))
            _write_string(buf, str(vaval))

        v_type = NC_FLOAT
        v_size = variables[vname].size * 4
        buf.write(struct.pack(">i", v_type))
        buf.write(struct.pack(">i", v_size))
        buf.write(struct.pack(">i", 0))  # Placeholder for begin offset

    # Header padding to 4 bytes
    pad = (4 - (buf.tell() % 4)) % 4
    if pad:
        buf.write(b"\x00" * pad)

    # Now rewrite var array with exact begin offsets
    data_start = buf.tell()
    var_data_bytes = []
    offsets = []
    curr_offset = data_start

    for vname in var_names:
        arr = np.asarray(variables[vname], dtype=">f4")
        b = arr.tobytes()
        pad = (4 - (len(b) % 4)) % 4
        if pad:
            b += b"\x00" * pad
        offsets.append(curr_offset)
        var_data_bytes.append(b)
        curr_offset += len(b)

    # Re-write the header with actual offsets
    buf.seek(var_header_pos)
    for idx, vname in enumerate(var_names):
        _write_string(buf, vname)
        vdims = var_dims.get(vname, [])
        buf.write(struct.pack(">i", len(vdims)))
        for vd in vdims:
            buf.write(struct.pack(">i", dim_names.index(vd)))

        vatts = var_attrs.get(vname, {})
        buf.write(struct.pack(">i", 0x0000000C))
        buf.write(struct.pack(">i", len(vatts)))
        for vaname, vaval in vatts.items():
            _write_string(buf, vaname)
            buf.write(struct.pack(">i", NC_CHAR))
            _write_string(buf, str(vaval))

        v_type = NC_FLOAT
        v_size = variables[vname].size * 4
        buf.write(struct.pack(">i", v_type))
        buf.write(struct.pack(">i", v_size))
        buf.write(struct.pack(">i", offsets[idx]))

    buf.seek(data_start)
    for b in var_data_bytes:
        buf.write(b)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(buf.getvalue())


def _write_string(buf: io.BytesIO, s: str) -> None:
    b = s.encode("utf-8")
    buf.write(struct.pack(">i", len(b)))
    buf.write(b)
    pad = (4 - (len(b) % 4)) % 4
    if pad:
        buf.write(b"\x00" * pad)


def load_netcdf(path: Union[str, Path]) -> NetCDFDataset:
    """
    Universal NetCDF loader:
    1. Tries scipy.io.netcdf / netCDF4 / xarray if installed.
    2. Falls back to PurePythonNetCDF3Reader for native binary NetCDF-3 files.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"NetCDF file does not exist: {file_path}")

    # Check for installed NetCDF libraries first
    try:
        import scipy.io.netcdf as sp_nc  # type: ignore
        with sp_nc.netcdf_file(str(file_path), "r", mmap=False) as nc:
            ds = NetCDFDataset(str(file_path))
            for d_name, d_len in nc.dimensions.items():
                ds.dimensions[d_name] = d_len
            for v_name, v_var in nc.variables.items():
                ds.variables[v_name] = np.array(v_var.data)
                ds.var_attributes[v_name] = dict(getattr(v_var, "_attributes", {}))
            ds.attributes = dict(getattr(nc, "_attributes", {}))
            return ds
    except ImportError:
        pass
    except Exception as e:
        logger.debug("scipy.io.netcdf load failed, falling back to pure python: %s", e)

    try:
        import netCDF4  # type: ignore
        with netCDF4.Dataset(str(file_path), "r") as nc:
            ds = NetCDFDataset(str(file_path))
            for d_name, dim in nc.dimensions.items():
                ds.dimensions[d_name] = len(dim)
            for v_name, var in nc.variables.items():
                ds.variables[v_name] = np.array(var[:])
                ds.var_attributes[v_name] = {k: var.getncattr(k) for k in var.ncattrs()}
            ds.attributes = {k: nc.getncattr(k) for k in nc.ncattrs()}
            return ds
    except ImportError:
        pass
    except Exception as e:
        logger.debug("netCDF4 load failed, falling back to pure python: %s", e)

    # Use pure Python NetCDF-3 binary parser
    return PurePythonNetCDF3Reader.read(file_path)
