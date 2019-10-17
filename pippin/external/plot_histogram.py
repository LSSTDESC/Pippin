import numpy as np
import pandas as pd
import sys
import argparse
import logging
import matplotlib.pyplot as plt
from scipy.stats import binned_statistic, moment


def setup_logging():
    fmt = "[%(levelname)8s |%(funcName)21s:%(lineno)3d]   %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    logging.basicConfig(level=logging.DEBUG, format=fmt, handlers=[handler, logging.FileHandler("plot_biascor.log")])
    logging.getLogger("matplotlib").setLevel(logging.ERROR)
    logging.getLogger("chainconsumer").setLevel(logging.WARNING)


def get_arguments():
    # Set up command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data", help="FITRES files with data", nargs="*", type=str, default=[])
    parser.add_argument("-s", "--sims", help="FITRES files with sims", nargs="*", type=str, default=[])
    parser.add_argument("-t", "--types", help="Ia types, space separated list", type=int, nargs="*", default=[])
    parser.add_argument("--done_file", help="Path of done file", type=str, default="done3.txt")
    args = parser.parse_args()

    logging.info(str(args))
    return args


def load_file(file):
    logging.info(f"Loading file {file}")
    df = pd.read_csv(file, delim_whitespace=True, comment="#")
    return df


def plot_histograms(data, sims, types):

    fig, axes = plt.subplots(2, 4, figsize=(9, 5))
    cols = ["x1", "c", "zHD", "FITPROB", "SNRMAX1", "cERR", "x1ERR", "PKMJDERR"]

    for c, ax in zip(cols, axes.flatten()):
        minv = min([x[c].quantile(0.01) for x in data + sims])
        maxv = max([x[c].quantile(0.99) for x in data + sims])
        bins = np.linspace(minv, maxv, 20)  # Keep binning uniform.
        bc = 0.5 * (bins[1:] + bins[:-1])

        for d in data:
            hist, _ = np.histogram(d[c], bins=bins)
            err = np.sqrt(hist)
            area = (bins[1] - bins[0]) * hist.sum()
            ax.errorbar(bc, hist / area, yerr=err / area, fmt="o", c="k", ms=2, elinewidth=0.75)

        for s in sims:
            mask = np.isin(s["TYPE"], types)
            ia = s[mask]
            nonia = s[~mask]

            hist, _ = np.histogram(s[c], bins=bins)
            area = (bins[1] - bins[0]) * hist.sum()

            ax.hist(s[c], bins=bins, histtype="step", weights=np.ones(s[c].shape) / area)
            ax.hist(ia[c], bins=bins, histtype="step", weights=np.ones(ia[c].shape) / area, linestyle="--")
            ax.hist(nonia[c], bins=bins, histtype="step", weights=np.ones(nonia[c].shape) / area, linestyle=":")

        ax.set_xlabel(c)
    fig.tight_layout()
    fig.savefig("hist.png", bbox_inches="tight", dpi=150, transparent=True)


def get_means_and_errors(x, y, bins):
    means, *_ = binned_statistic(x, y, bins=bins, statistic="mean")
    err, *_ = binned_statistic(x, y, bins=bins, statistic=lambda x: np.std(x) / np.sqrt(x.size))

    std, *_ = binned_statistic(x, y, bins=bins, statistic=lambda x: np.std(x))
    std_err, *_ = binned_statistic(
        x, y, bins=bins, statistic=lambda x: np.sqrt((1 / x.size) * (moment(x, 4) - (((x.size - 3) / (x.size - 1)) * np.var(x) ** 2))) / (2 * np.std(x))
    )
    return means, err, std, std_err


def plot_redshift_evolution(data, sims, types):

    fig, axes = plt.subplots(2, 2, figsize=(6, 4), sharex=True, gridspec_kw={"hspace": 0.0})
    cols = ["x1", "c"]

    for c, row in zip(cols, axes.T):
        ax0, ax1 = row

        minv = min([x["zHD"].min() for x in data + sims])
        maxv = max([x["zHD"].max() for x in data + sims])
        bins = np.linspace(minv, maxv, 10)  # Keep binning uniform.
        bc = 0.5 * (bins[1:] + bins[:-1])
        lim = (bc[0] - 0.02 * (bc[-1] - bc[0]), bc[-1] + 0.02 * (bc[-1] - bc[0]))
        for d in data:

            means, err, std, std_err = get_means_and_errors(d["zHD"], d[c], bins=bins)
            ax0.errorbar(bc, means, yerr=err, fmt="o", c="k", ms=2, elinewidth=0.75, zorder=20)
            ax1.errorbar(bc, std, yerr=std_err, fmt="o", c="k", ms=2, elinewidth=0.75, zorder=20)

        for sim in sims:
            mask = np.isin(sim["TYPE"], types)
            ia = sim[mask]
            nonia = sim[~mask]

            for s, ls, z in [(sim, "-", 10), (ia, "--", 3), (nonia, ":", 2)]:
                means, err, std, std_err = get_means_and_errors(s["zHD"], s[c], bins=bins)
                ax0.plot(bc, means, ls=ls, zorder=z)
                ax0.fill_between(bc, means - err, means + err, alpha=0.1, zorder=z)
                ax1.plot(bc, std, ls=ls, zorder=z)
                ax1.fill_between(bc, std - std_err, std + std_err, alpha=0.1, zorder=z)

        ax0.set_ylabel(f"Mean {c}")
        ax1.set_ylabel(f"Std {c}")
        ax0.set_xlim(*lim)
        ax1.set_xlim(*lim)
    axes[1, 0].set_xlabel("z")
    axes[1, 1].set_xlabel("z")
    fig.tight_layout()
    fig.savefig("redshift.png", bbox_inches="tight", dpi=150, transparent=True)


if __name__ == "__main__":
    setup_logging()
    args = get_arguments()
    try:
        if not args.data:
            logging.warning("Warning, no data files specified")
        if not args.sims:
            logging.warning("Warning, no sim files specified")
        if not args.types:
            logging.warning("Warning, no Ia types specified, assuming 1 and 101.")
            args.types = [1, 101]

        data_dfs = [load_file(f) for f in args.data]
        sim_dfs = [load_file(f) for f in args.sims]

        plot_histograms(data_dfs, sim_dfs, args.types)
        plot_redshift_evolution(data_dfs, sim_dfs, args.types)

        logging.info(f"Writing success to {args.done_file}")
        with open(args.done_file, "w") as f:
            f.write("SUCCESS")
    except Exception as e:
        logging.exception(str(e))
        logging.error(f"Writing failure to file {args.done_file}")
        with open(args.done_file, "w") as f:
            f.write("FAILURE")