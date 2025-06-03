from typing import Union, Optional, Callable
from pathlib import Path
from antares.craft.model.area import Area
from antares.craft.model.study import Study
from antares.craft.model.thermal import ThermalCluster
# from antares.craft.model.area import BindingConstraint
from antares.craft.model.binding_constraint import BindingConstraint
import pandas as pd
from andromede.input_converter.src.utils import check_file_exists, check_dataframe_validity
from antares.craft.tools.time_series_tool import TimeSeriesFileType
from antares.craft.tools.matrix_tool import read_timeseries
from andromede.input_converter.src.data_preprocessing.dataclasses import (
    TimeseriesData,
    BindingConstraintData,
    ThermalData,
    LoadData,
    SolarData,
    WindData,
    ReservesData,
    MiscGenData,
    LinksData,
    Operation,
    )

FIELD_ALIAS_MAP = {
    "nominalcapacity": "nominal_capacity",
    "min-stable-power": "min_stable_power",
    "min-up-time": "min_up_time",
    "min-down-time": "min_down_time"}

type_to_data_class = {
    "timeseries": TimeseriesData,
    "binding_constraint": BindingConstraintData,
    "thermal": ThermalData,
    "load": LoadData,
    "solar": SolarData,
    "wind": WindData,
    "reserves": ReservesData,
    "misc_gen": MiscGenData,
    "link": LinksData,
}


DataType = Union[ThermalData, TimeseriesData, BindingConstraintData, LoadData, SolarData, WindData, ReservesData, MiscGenData]

class BindingConstraintsPreprocessing:
    preprocessed_values: dict[str, float] = {}
    id: Optional[str] = None

    def __init__(self, study: Study):
        self.study = study
        self.study_path: Path = study.service.config.study_path
        
    def _process_time_series(
        self,
        area_id: str,
        obj
    ) -> Union[float, str]:
        area: Area = self.study.get_areas()[area_id]
        ts_file_type = getattr(TimeSeriesFileType, obj.timeseries_file_type.upper())
        second_area_id=obj.area_to if isinstance(obj, LinksData) else None
        cluster_id=obj.cluster if isinstance(obj, ThermalData) else None

        input_path = self.study_path / ts_file_type.value.format(
            area_id=area_id, cluster_id=cluster_id, second_area_id=second_area_id
        )
        try:
            _time_series = read_timeseries(ts_file_type, self.study_path, area_id, cluster_id=cluster_id, second_area_id=second_area_id)
            
        except FileNotFoundError:
            # TODO
            # Just return the path as the file doesnt exist
            return str(input_path.parent)

        filtered_time_series = _time_series.iloc[:, obj.column]

        output_file = input_path.parent / f"{self.id}_{area.id}.txt"
        if obj.operation:
            parameter_value: Union[float, pd.Series] = obj.operation.execute(
                filtered_time_series, self.preprocessed_values
            )
            if isinstance(parameter_value, float):
                self.preprocessed_values[self.id] = parameter_value
                return parameter_value
            if isinstance(parameter_value, pd.Series):
                parameter_value.to_csv(output_file, sep="\t", index=False, header=False)
        else:
            filtered_time_series.to_csv(output_file, sep="\t", index=False, header=False)

        return str(output_file.parent / f"{self.id}_{area.id}")

    def calculate_value(self, obj: DataType) -> Union[float, str]:
        if isinstance(obj, ThermalData):
            if obj.timeseries_file_type is not None:
                return self._process_time_series(obj.area, obj)
            area = self.study.get_areas()[obj.area]
            thermal: ThermalCluster = area.get_thermals()[obj.cluster]
            field_name = FIELD_ALIAS_MAP[obj.field]
            parameter_value = getattr(thermal.properties, field_name)
            self.preprocessed_values[self.id] = parameter_value
            return parameter_value
        elif isinstance(obj, TimeseriesData):
            input_path = self.study_path / obj.path
            if check_file_exists(input_path) and check_dataframe_validity(pd.read_csv(input_path, sep="\t", header=None)):
                _time_series = pd.read_csv(input_path, sep="\t", header=None)
                filtered_time_series = _time_series.iloc[:, obj.column]
                if obj.operation:
                    parameter_value: Union[float, pd.Series] = obj.operation.execute(filtered_time_series, self.preprocessed_values)
                    if isinstance(parameter_value, float):
                        self.preprocessed_values[self.id] = parameter_value
                    if isinstance(parameter_value, pd.Series):
                        parameter_value.to_csv(input_path.parent / f"{self.id}.txt", sep="\t", index=False, header=False)
                        parameter_value = str(input_path.parent / self.id)
                    return parameter_value
                else:
                    filtered_time_series.to_csv(input_path.parent / f"{self.id}.txt", sep="\t", index=False, header=False)
                    return str(input_path.parent / self.id)
            else:
                _time_series = pd.DataFrame()
                _time_series.to_csv(input_path.parent / f"{self.id}.txt", sep="\t", index=False, header=False)
            return str(input_path.parent / self.id)

        elif isinstance(obj, BindingConstraintData):
            return "mock"
            bindings: BindingConstraint = self.study.get_binding_constraints()[obj.id]
            parameter_value = bindings.get_terms()[obj.field]
            parameter_value: float = obj.operation.execute(parameter_value)
            return parameter_value
        elif isinstance(obj, LinksData):
            return self._process_time_series(obj.area_from, obj)
        else:
            return self._process_time_series(obj.area, obj)



    def convert_param_value(self, id: str, parameter: dict) -> Union[str, float]:
        self.id = id
        value_type = parameter["type"]

        cls = type_to_data_class.get(value_type)

        data = parameter.get("data")

        if value_type == "constant":
            return float(data)
        
        if not cls:
            raise ValueError(f"Unknown value type: {value_type}")
        
        if "operation" in data:
            data["operation"] = Operation(**data["operation"])
        
        return self.calculate_value(cls(**data))
