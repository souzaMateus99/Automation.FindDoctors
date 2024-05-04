import json
import re
import urllib
from enum import StrEnum, auto
import urllib.parse
import pandas as pd

import requests
from bs4 import BeautifulSoup


class EnumSpeciality(StrEnum):
    Neurologista = auto()


def factory_beautiful_soup(html_content: str) -> BeautifulSoup:
    """Create BeautifulSoup object with the parameter 'features="html.parser"'

    Args:
        html_content (str): Sting with html content to send to BeautifulSoup object

    Returns:
        BeautifulSoup: BeautifulSoup object
    """
    return BeautifulSoup(html_content, features="html.parser")


class Doctor:
    """Doctor object"""

    def __init__(self, name, specialty, doctoralia_url):
        """Doctor object

        Args:
            name (_type_): The doctor's name
            specialty (_type_): The doctor's speciality
            doctoralia_url (_type_): The doctor's url from 'doctoralia'
        """
        self.name = name
        self.crm = ""
        self.specialty = specialty
        self.url = doctoralia_url
        self.service_addresses = []

    def add_service_address(self, city, street_address):
        self.service_addresses.append({"city": city, "street": street_address})

    def get_doctor(self):
        return {
            "name": self.name,
            "crm": self.crm,
            "speciality": self.specialty,
            "doctoralia_url": self.url,
            "addresses": self.service_addresses,
        }


class DoctorPage:
    def __init__(self, doctor: Doctor):
        self.__doctor = doctor

    def process(self) -> Doctor:
        response = requests.get(self.__doctor.url)
        soup = factory_beautiful_soup(response.text)

        doctor_register_element = soup.find(name="p", attrs={"class": "text-body mb-1"})

        if doctor_register_element:
            doctor_register = re.search(
                "CRM[\\s:]*(?P<local1>\\D{2})?[\\s]*(?P<crm>[\\d]+)[\\s-]*(?P<local2>\\w{2})?",
                doctor_register_element.text.strip()
                .replace("\t", "")
                .replace("\n", ""),
                re.IGNORECASE,
            )

            if doctor_register:
                local = (
                    doctor_register.group("local1")
                    if doctor_register.group("local1")
                    else doctor_register.group("local2")
                )
                crm = doctor_register.group("crm")

                self.__doctor.crm = crm = f"{crm} {local}"

        doctor_address_elements = soup.find_all(
            name="h5", attrs={"class": "m-0 font-weight-normal"}
        )

        for doctor_address_element in doctor_address_elements:
            doctor_properties = {}
            for child in doctor_address_element.children:
                if child.name == "span":
                    if child.attrs["itemprop"] == "streetAddress":
                        for c in child.children:
                            if c.name == "span":
                                if (
                                    c["data-test-id"]
                                    and c["data-test-id"] == "address-info-street"
                                ):
                                    doctor_properties["addressStreet"] = c.text
                                    break
                    else:
                        doctor_properties[child.attrs["itemprop"]] = child.attrs[
                            "content"
                        ]

            self.__doctor.add_service_address(
                (
                    doctor_properties["addressLocality"]
                    if doctor_properties.get("addressLocality")
                    else ""
                ),
                (
                    doctor_properties["addressStreet"]
                    if doctor_properties.get("addressStreet")
                    else ""
                ),
            )

        return self.__doctor


class DoctorListPage:
    def __init__(self, html_content):
        self.__content = html_content

    def process(self) -> list[DoctorPage]:
        soup = factory_beautiful_soup(self.__content)
        doctor_list_element = soup.find(
            name="ul", attrs={"class": "list-unstyled search-list"}
        )

        doctor_item_elements = []

        for table_element_item in doctor_list_element.contents:
            if table_element_item.name == "li":
                for child in table_element_item.children:
                    if child.name == "div":
                        doctor_item_elements.append(child)

        doctors_page = []

        for doctor_card_element in doctor_item_elements:
            doctor_name = doctor_card_element["data-doctor-name"]
            doctor_url = doctor_card_element["data-doctor-url"]
            doctor_specialty = doctor_card_element["data-eecommerce-category"]
            doc = Doctor(doctor_name, doctor_specialty, doctor_url)
            doctor_page = DoctorPage(doc)
            doctors_page.append(doctor_page)

        return doctors_page


class SearchResultPage:
    def __init__(self, speciality: EnumSpeciality, localization):
        spec = urllib.parse.quote(speciality.value)
        local = urllib.parse.quote(localization)

        self.__url = f"https://www.doctoralia.com.br/pesquisa?q={spec}&loc={local}"

    def process(self) -> DoctorListPage:
        response = requests.get(self.__url)
        return DoctorListPage(response.text)


doctor_list_page = SearchResultPage(
    EnumSpeciality.Neurologista, "Itaquaquecetuba, SP"
).process()
doctors_page = doctor_list_page.process()

doctors = []

for doctor_page in doctors_page:
    doctor = doctor_page.process()
    doctors.append(doctor)

dfs = []

for doctor in doctors:
    df = pd.DataFrame(doctor.get_doctor())
    dfs.append(df)

df_doctor = pd.concat(dfs)
df_doctor.to_parquet("doctors.parquet", engine="pyarrow", compression="snappy")
