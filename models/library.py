class Library:
    def __init__(self, serial_number, name, district, address, phone, website, operating_hours, closed_days, library_type, latitude, longitude):
        self.serial_number = serial_number
        self.name = name
        self.district = district
        self.address = address
        self.phone = phone
        self.website = website
        self.operating_hours = operating_hours
        self.closed_days = closed_days
        self.library_type = library_type
        self.latitude = latitude
        self.longitude = longitude

    def matches_keyword(self, keyword):
        keyword = keyword.lower()

        return (
            keyword in str(self.name).lower()
            or keyword in str(self.district).lower()
            or keyword in str(self.address).lower()
        )
    @classmethod
    def from_row(cls, row):
        return cls(
            serial_number=row["Library_Serial_Number"],
            name=row["Library_Name"],
            district=row["District_Name"],
            address=row["Address"],
            phone=row["Phone_Number"],
            website=row["Website_URL"],
            operating_hours=row["Operating_Hours"],
            closed_days=row["Regular_Closed_Days"],
            library_type=row["Library_Type_Name"],
            latitude=row["Latitude"],
            longitude=row["Longitude"]
    )

    def details(self):
        return {
            "District": self.district,
            "Address": self.address,
            "Phone": self.phone,
            "Operating Hours": str(self.operating_hours).replace("~", " - "),
            "Closed Days": self.closed_days,
            "Website": self.website,
        }