"""Адаптеры источников. Новый реестр: папка adapters/<source>/ + строка в ADAPTERS."""

from storozh.documents.adapters.mygov_car_poa.adapter import MyGovCarPoaAdapter
from storozh.documents.adapters.mygov_career.adapter import MyGovCareerAdapter
from storozh.documents.adapters.mygov_notarial.adapter import MyGovNotarialAdapter
from storozh.documents.adapters.mygov_notifications.adapter import MyGovNotificationsAdapter
from storozh.documents.adapters.mygov_requests.adapter import MyGovRequestsAdapter
from storozh.documents.adapters.vakolat.adapter import VakolatAdapter
from storozh.documents.ports import SourceAdapter

ADAPTERS: list[SourceAdapter] = [
    MyGovCarPoaAdapter(), MyGovRequestsAdapter(), MyGovNotificationsAdapter(), MyGovCareerAdapter(),
    MyGovNotarialAdapter(), VakolatAdapter(),
]
