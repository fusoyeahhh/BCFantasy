import gspread
from gspread_dataframe import set_with_dataframe

def export_to_gsheet(season, ndoc=0):
    """
    Export a `pandas.DataFrame` to a google sheet. Used to synch the season leaderboard.

    :param season: `pandas.DataFrame` to synch
    :param ndoc: Identifier of the sheet to synch
    :return: None
    """

    gc = gspread.service_account()
    sh = gc.open('Season Leaderboard')
    worksheet = sh.get_worksheet(ndoc)
    worksheet.format ('1', {'textFormat': {'bold': True}})
    set_with_dataframe(worksheet, season)