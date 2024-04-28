import io
import requests, json, re
from bs4 import BeautifulSoup


class Doctor:
    def __init__(self, name, specialty, doctoralia_url):
        self.name = name
        self.crm = ""
        self.specialty = specialty
        self.url = doctoralia_url
        self.service_addresses = []

    def add_service_address(self, city, street_address):
        self.service_addresses.append({"city": city, "street": street_address})

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class DoctorPage:
    def __init__(self, doctor: Doctor):
        self.__doctor = doctor

    def process(self) -> Doctor:
        response = requests.get(self.__doctor.url)
        soup = BeautifulSoup(response.text)

        doctor_register_element = soup.find(name="p", attrs={"class": "text-body mb-1"})

        doctor_register = re.match(
            "CRM[\\s:]*(?P<local1>\\D{2})?[\\s]*(?P<crm>[\\d]+)[\\s-]*(?P<local2>\\w{2})?",
            doctor_register_element.text.strip().replace("\t", "").replace("\n", ""),
            re.IGNORECASE,
        )

        if doctor_register:
            local = doctor_register.group("local1")
            crm = doctor_register.group("crm")
            local = doctor_register.group("local2")

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
                    doctor_properties["addressLocality"],
                    doctor_properties["addressStreet"],
                )


class DoctorListPage:
    def __init__(self, html_content):
        self.__content = html_content

    def process(self) -> list[DoctorPage]:
        soup = BeautifulSoup(self.__content)
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
    def __init__(self, speciality, localization):
        self.__url = (
            f"https://www.doctoralia.com.br/pesquisa?q={speciality}&loc={localization}"
        )

    def process(self) -> DoctorListPage:
        response = requests.get(self.__url)
        return DoctorListPage(response.text)


doctor_list_page = SearchResultPage("Neurologista", "Itaquaquecetuba%2C%20SP").process()
doctors_page = doctor_list_page.process()

for doctor_page in doctors_page:
    doctor = doctor_page.process()
    print(doctor.to_json())
