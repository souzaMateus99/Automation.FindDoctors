import io
import requests, json, re
from bs4 import BeautifulSoup

class Doctor():
    def __init__(self, name, specialty, doctoralia_url):
        self.name = name
        self.crm = ""
        self.specialty = specialty
        self.url = doctoralia_url
        self.service_addresses = []

    def add_service_address(self, city, address):
        self.service_addresses.append({
            "city": city,
            "address": address
        })

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

r = requests.get("https://www.doctoralia.com.br/pesquisa?q=Neurologista&loc=Itaquaquecetuba%2C%20SP&filters%5Bspecializations%5D%5B0%5D=60&page=1")
soup = BeautifulSoup(r.text)
doctors_page_list = soup.find(name="ul", attrs={"class": "list-unstyled search-list"})

doctors_element_list = []

for child in doctors_page_list.contents:
    if child.name == "li":
        doctors_element_list.append(child)

doctor_cards = []

for doctor_element in doctors_element_list:
    for doctor_element_child in doctor_element.contents:
        if doctor_element_child.name == "div":
            doctor_cards.append(doctor_element_child)

doctors = []

for doctor_card in doctor_cards:
    doctor_name = doctor_card["data-doctor-name"]
    doctor_url = doctor_card["data-doctor-url"]
    doctor_specialty = doctor_card["data-eecommerce-category"]
    doctors.append(Doctor(doctor_name, doctor_specialty, doctor_url))

for doctor in doctors:
    doctor_page = requests.get(doctor.url)

    soup = BeautifulSoup(doctor_page.text)
    doctor_content_info = soup.find("div", attrs={"class": "media-body d-flex flex-column overflow-hidden"})
    if doctor_content_info:
        for child in doctor_content_info.contents:
            if child.name == "div" and "text-muted" in child["class"] and "small" in child["class"]:
                doctor.crm = re.search(r"crm:?[\s\D]*([\d]+)", child.text, re.I).group(1)
                break

    doctor_address_info = soup.find("div", attrs={"data-id": "address-tabs-content"})
    
    for child in doctor_address_info.contents[0]:
        if child.name == "div" and child["itemprop"] == "address":
            for child_2 in child.contents:
                print("a")

    print(doctor.to_json())

print("a")
# io.open("teste.html", mode="w", encoding="utf-8").write(r.text)