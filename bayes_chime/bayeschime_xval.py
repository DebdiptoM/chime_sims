


'''
Bayes chime cross-validation:
Run regular chime-sims then bayes chime, holding out data along the way to check performance

'''
import pandas as pd
pd.options.display.max_rows = 4000
pd.options.display.max_columns = 4000
import os
from typing import Dict, Tuple

from argparse import ArgumentParser

from datetime import date as Date
from datetime import timedelta

from pandas import DataFrame, date_range, read_csv
from scipy.stats import expon

from gvar import dump, mean, sdev

from gvar._gvarcore import GVar  # pylint: disable=E0611
from gvar import gvar
from lsqfit import nonlinear_fit, empbayes_fit


from bayes_chime.normal.utilities import (
    FloatOrDistVar,
    FloatLike,
    NormalDistVar,
    NormalDistArray,
    one_minus_logistic_fcn,
)

from bayes_chime.normal.models import SEIRModel
from bayes_chime.normal.scripts.utils import (
    DEBUG,
    read_parameters,
    read_data,
    dump_results,
    get_logger,
)
import numpy as np

datadir = f"{os.getcwd()}/data/"

os.listdir(datadir)


def logisitic_social_policy(
    date: Date, **kwargs: Dict[str, FloatOrDistVar]
) -> Dict[str, FloatOrDistVar]:
    """Updates beta parameter as a function of time by multiplying base parameter
    with 1 - logistic function.

    Relevant keys are:
        * dates
        * beta
        * logistic_L
        * logistic_k
        * logistic_x0
    """
    xx = (date - kwargs["dates"][0]).days
    ppars = kwargs.copy()
    ppars["beta"] = kwargs["beta"] * one_minus_logistic_fcn(
        xx, L=kwargs["logistic_L"], k=kwargs["logistic_k"], x0=kwargs["logistic_x0"],
    )
    return ppars


def prepare_model_parameters(
    parameters: Dict[str, FloatOrDistVar], data: DataFrame
) -> Tuple[Dict[str, FloatLike], Dict[str, NormalDistVar]]:
    """Prepares model input parameters and returns independent and dependent parameters

    Also shifts back simulation to start with only exposed people.
    """

    # Set up fit parameters
    ## Dependent parameters which will be fitted
    pp = {key: val for key, val in parameters.items() if isinstance(val, GVar)}
    ## Independent model meta parameters
    xx = {key: val for key, val in parameters.items() if key not in pp}

    # This part ensures that the simulation starts with only exposed persons
    ## E.g., we shift the simulation backwards such that exposed people start to
    ## become infected
    xx["offset"] = int(
        expon.ppf(0.99, 1 / pp["incubation_days"].mean)
    )  # Enough time for 95% of exposed to become infected
    pp["logistic_x0"] += xx["offset"]

    ## Store the actual first day
    xx["day0"] = data.index.min()
    ## And start earlier in time
    xx["dates"] = date_range(
        xx["day0"] - timedelta(xx["offset"]), freq="D", periods=xx["offset"]
    ).union(data.index)

    ## Thus, all compartment but exposed and susceptible are 0
    for key in ["infected", "recovered", "icu", "vent", "hospital"]:
        xx[f"initial_{key}"] = 0

    pp["initial_exposed"] = (
        xx["n_hosp"] / xx["market_share"] / pp["hospital_probability"]
    )
    xx["initial_susceptible"] -= pp["initial_exposed"].mean

    return xx, pp


def get_yy(data: DataFrame, **err: Dict[str, FloatLike]) -> NormalDistArray:
    """Converts data to gvars by adding uncertainty:

    yy_sdev = yy_mean * rel_err + min_er
    """
    return gvar(
        [data["hosp"].values, data["vent"].values],
        [
            data["hosp"].values * err["hosp_rel"] + err["hosp_min"],
            data["vent"].values * err["vent_rel"] + err["vent_min"],
        ],
    ).T



days_withheld = 7
which_hospital = "HUP"
def bayes_xval(days_withheld = 7, which_hospital = "HUP"):
    parameters = read_parameters(f"{datadir}{which_hospital}_parameters.csv")
    data = read_data(f"{datadir}{which_hospital}_ts.csv")[:-days_withheld]
    test_set = pd.read_csv(f"{datadir}{which_hospital}_ts.csv")[-days_withheld:]
    test_set.date = test_set.date.astype("datetime64[ns]")
    model = SEIRModel(
        fit_columns=["hospital_census", "vent_census"],
        update_parameters=logisitic_social_policy,
    )
    
    xx, pp = prepare_model_parameters(parameters, data)
    model.fit_start_date = xx["day0"]

    fit_kwargs = lambda error_infos: dict(
        data=(xx, get_yy(data, hosp_rel=0, vent_rel=0, **error_infos)),
        prior=pp,
        fcn=model.fit_fcn,
        debug=True,
    )
    fit, xx["error_infos"] = empbayes_fit(
        {"hosp_min": 10, "vent_min": 1}, fit_kwargs
    )
    # extend by 60 days
    xx["dates"] = xx["dates"].union(
        date_range(xx["dates"].max(), freq="D", periods=60)
    )
    prediction_df = model.propagate_uncertainties(xx, fit.p)
    prediction_df.index = prediction_df.index.round("H")
    
    # drop the index
    prediction_df = prediction_df.reset_index()
    prediction_df['hmu'] = prediction_df.hospital_census.apply(lambda x: float(str(x).split("(")[0]))
    prediction_df['hsig'] = prediction_df.hospital_census.apply(lambda x: float(str(x).split("(")[1][:-1]) if "(" in str(x) else float(x))
    prediction_df['vmu'] = prediction_df.vent_census.apply(lambda x: float(str(x).split("(")[0]))
    prediction_df['vsig'] = prediction_df.vent_census.apply(lambda x: float(str(x).split("(")[1][:-1]) if "(" in str(x) else float(x))

    # merge
    mm = prediction_df.merge(test_set, how = 'left')
    data.columns = ["obs_"+ i for i in data.columns]
    data.reset_index(inplace = True)
    mm = mm.merge(data, how = 'outer')
    
    # compute simple msfe
    hRMSFE = np.mean((mm.hmu - mm.hosp)**2)**.5
    vRMSFE = np.mean((mm.vmu - mm.vent)**2)**.5

    # now run MCMC
    df = do_chains(.05, )
    
    _01_GOF_sims.py -p <parameters_file> -t <ts_file> -C <n_chains> -i <n_iters>

from _01_GOF_sims import do_chains



df = GOF_sims(True, **dict(n_chains = 10,
                           N_ITERS = 2,
                           penalty = 0.05,
                           fit_penalty = False,
                           as_of = days_withheld,
                           df = True,
                           sample_obs = False))
                           
        penalty = kwargs['penalty']
        fit_penalty = kwargs['fit_penalty']
        sample_obs = kwargs['sample_obs']
        as_of_days_ago = kwargs['as_of']
        return_a_data_frame = kwargs['df'])



import main from _01

    
    