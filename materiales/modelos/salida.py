# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
import pandas as pd
from typing import List


@dataclass(slots=True)
class ResultadoMateriales:
    ok: bool
    df_materiales: pd.DataFrame
    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
