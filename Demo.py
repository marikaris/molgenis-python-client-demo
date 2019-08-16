from molgenis import client as molgenis
from yaspin import yaspin
from termcolor import cprint
from natsort import natsorted
import time
import sys
import random
import names
import datetime
import math
import getpass


class NextStep:
    def __init__(self):
        user_input = input("Press Enter to continue (To Quit, type q + Enter)\n")
        if user_input.lower() == 'q':
            sys.exit()


class Execute:
    def __init__(self):
        self.user_input = input("\nExecute? (Enter = Yes, n + Enter = No)\nPress q + Enter to Quit\n")
        if self.user_input.lower() == 'q':
            sys.exit()

    def do_execute(self):
        if self.user_input.lower() == 'n':
            return False
        else:
            return True


cprint("""################################## MOLGENIS API CLIENT DEMONSTRATION ##################################
# Before starting:
# - Start molgenis version 8 or higher on http://localhost:8080, or configure an alternative URL with a Molgenis in the
# tutorial below
# - Use PyCharm to write your python code (shortcuts in this tutorial will be given for PyCharm exclusively)
#
# This tutorial script contains two classes:
# - The MolgenisDatabase class will do all Molgenis related calls and is a sort of wrapper around the client to make it
#   more understandable.
# - The HospitalSimulation class contains the example we will use to explain the API client. It contains datamodel
#   specific code and will also use other python libraries.
#
# To start with this tutorial scroll down to the main function. The steps of the tutorial will be described shortly.
# After the description in comments, a few lines of code will follow. ctrl/cmd + click on the functions in the code
# to see the actual code that is behind the function.
#
# Ctrl/cmd + ?/ key to uncomment lines (you may want to skip deleting and uploading data after doing it once).
""", 'blue')
NextStep()


class MolgenisDatabase:
    def __init__(self, molgenis_server, admin_password):

        api_url = molgenis_server + '/api/'
        # Create molgenis session with specified server
        self.molgenis_client = molgenis.Session(api_url)
        # Login as admin to server
        self.molgenis_client.login('admin', admin_password)

    def upload_data(self, file_to_upload):
        # Response is an URL on which the status of the import can be checked
        # Uploading files (datamodels) can be done using the upload_zip endpoint
        response = self.molgenis_client.upload_zip(file_to_upload)
        self.check_status(response)

    def check_status(self, url):
        # Split the URL and get the last part of it (=id)
        entity_id = url.split('/')[-1]
        import_run = self.molgenis_client.get_by_id('sys_ImportRun', entity_id)
        status = import_run['status']

        # Poll the status
        with yaspin(text='Uploading data', color='green') as spinner:
            while status == 'RUNNING':
                # Build in some sleep to prevent the script from spamming the server too much
                time.sleep(2)
                import_run = self.molgenis_client.get_by_id('sys_ImportRun', entity_id)
                status = import_run['status']

            if status == 'FAILED':
                spinner.fail('💥')
                cprint('Import failed: {}'.format(import_run['message']), 'red', attrs=['bold'], file=sys.stderr)

            elif status == 'FINISHED':
                spinner.ok("✔")

    def get_total(self, entity_type):
        # Get data and meta data using the raw=True. By default raw = False, then the get request will only return the
        # items(=data) in the response.
        response = self.molgenis_client.get(entity_type, raw=True)
        return response['total']

    def get_meta(self, entity_type):
        response = self.molgenis_client.get(entity_type, raw=True)
        return response['meta']

    def get_with_query(self, entity_type, query):
        data = self.molgenis_client.get(entity_type, q=query)
        return data

    def get(self, entity_type):
        # Max number of values to retrieve is 10000, default num = 100
        data = self.molgenis_client.get(entity_type)
        return data

    def get_num(self, entity_type, num):
        data = self.molgenis_client.get(entity_type, num=num)
        return data

    def delete_package(self, package):
        response = self.molgenis_client.delete('sys_md_Package', package)
        response.raise_for_status()
        print('Package "{}" deleted'.format(package))

    def add_values(self, entity_type, values):
        # Max number of values per call = 1000
        # Values is a list of dictionaries. The dictionaries with as key the id of the column and as value the assigned
        # value that you also would use in an EMX data file. To select references (xref/categorical), provide the id
        # of the value you want to select. To select multiple references (mref/categorical mref), provide a list with
        # id's of your values as value of the column id.
        # Example of values:
        # [{id: "id1", reference: "val1", multiple: ["ref1", "ref2"]}]
        self.molgenis_client.add_all(entity_type, values)

    @staticmethod
    def generate_molgenis_date_from_datetime(datetime_element):
        month0 = '0' + str(datetime_element.month)
        month = month0[-2] + month0[-1]
        day0 = '0' + str(datetime_element.day)
        day = day0[-2] + day0[-1]
        return '{}-{}-{}'.format(datetime_element.year, month, day)


class HospitalSimulation:
    def __init__(self, molgenis_db):
        self.molgenis_db = molgenis_db
        self.last_patient_id = self.get_last_id('root_hospital_patients')
        self.new_patients = []

    @staticmethod
    def get_number_of_visits():
        return random.randint(1, 20)

    @staticmethod
    def get_number_of_existing_visits(total):
        return random.randint(0, total)

    def get_new_patients(self, total, existing):
        new_patients = []
        number_of_new_patients = total - existing
        for patient in range(number_of_new_patients):
            new_patient = self.get_new_patient()
            new_patients.append(new_patient)
        return new_patients

    def get_last_id(self, table):
        id_attr = self.molgenis_db.get_meta(table)['idAttribute']
        ids = [row[id_attr] for row in self.molgenis_db.get_num(table, 10000)]
        sorted_ids = natsorted(ids, key=lambda y: y.lower())
        return sorted_ids[-1]

    def get_next_id(self):
        id_number = int(self.last_patient_id[1::])
        new_number = id_number + 1
        # Generate a patient id with 9 numbers, ending with the new number, filling the rest with 0's
        new_id = 'p{}{}'.format('0' * (9 - len(str(new_number))), new_number)
        self.last_patient_id = new_id
        return new_id

    def get_random_date_of_birth(self):
        # https://gist.github.com/knu2xs/8ca7e0a39bf26f736ef7
        now = datetime.datetime.now()
        # Get random year, max 120 years ago and at minimum last year
        year = random.randint(now.year - 120, now.year - 1)
        # try to get a date
        try:
            dob = datetime.datetime.strptime('{} {}'.format(random.randint(1, 366), year), '%j %Y')
            return dob

        # if the value happens to be in the leap year range, try again
        except ValueError:
            self.get_random_date_of_birth()

    def get_random_patient(self):
        gender = 'male' if bool(random.getrandbits(1)) else 'female'
        name = names.get_full_name(gender)
        dob = self.molgenis_db.generate_molgenis_date_from_datetime(self.get_random_date_of_birth())
        first_name, last_name = name.split(' ')
        return {'firstName': first_name, 'lastName': last_name, 'birthdate': dob, 'gender': gender[0]}

    def get_new_patient(self):
        patient = self.get_random_patient()
        patient['id'] = self.get_next_id()
        return patient

    def register_new_patients(self, patients):
        self.molgenis_db.add_values('root_hospital_patients', patients)

    @staticmethod
    def get_existing_patients(number_of_existing_patients, existing_patients):
        return [existing_patients[index] for index in range(number_of_existing_patients)]

    def get_doctor_for_patient(self, patient_first_name, patient_last_name, doctors):
        doctor = doctors[random.randint(0, len(doctors) - 1)]
        # Patient cannot be treated by him or herself
        if doctor['firstName'] == patient_first_name and doctor['lastName'] == patient_last_name:
            self.get_doctor_for_patient(patient_first_name, patient_last_name, doctors)
        else:
            return doctor

    def get_doctors_description(self):
        doctors = self.molgenis_db.get_with_query('root_hospital_employees', query='function_description==dc')
        for doctor in doctors:
            cprint('\n{} {}'.format(doctor['firstName'], doctor['lastName']), 'magenta')

            functions = []
            for function in doctor['function_description']:
                functions.append(function['label'])
            cprint(', '.join(functions), 'magenta')

            department = None if not 'department' in doctor else doctor['department']['label']
            if department:
                cprint('dept. {}'.format(department), 'magenta')

    def get_family_of_patient_by_name(self, first_name, last_name):
        # Get the id of the patient by querying for the firstName and lastName
        patient_in_db = self.molgenis_db.get_with_query('root_hospital_patients',
                                                        'firstName=="{}";lastName=="{}"'.format(
                                                            first_name, last_name))[0]
        children_of_patient = [child['id'] for child in patient_in_db['children']]
        spouse = self.molgenis_db.get_with_query('root_hospital_patients', '{};gender!={}'.format(
            ';'.join(
                ['children=={}'.format(child) for child in children_of_patient]),
            patient_in_db['gender']['id']))[0]
        complete_family = [patient_in_db['id'], spouse['id']] + children_of_patient
        return complete_family

    def simulate_day(self):
        # Get current number of patients in the database.
        patients_in_db = self.molgenis_db.get_total('root_hospital_patients')
        cprint('\nThe day has started. Number of patients in database: {}'.format(patients_in_db), 'magenta')
        # Get number of patients in today
        number_visits = self.get_number_of_visits()
        # Determine how many of the existing patients are visiting and how many are new
        number_existing_patients = self.get_number_of_existing_visits(number_visits)
        # Get existing patients
        patients = self.molgenis_db.get('root_hospital_patients')
        existing_patients = self.get_existing_patients(number_existing_patients, patients)
        # Get the new patients
        new_patients = self.get_new_patients(number_visits, number_existing_patients)
        # register them if there are new patients
        if len(new_patients) > 0:
            self.register_new_patients(new_patients)
        # merge existing and new patients
        patients_visiting = new_patients + existing_patients
        # assign doctor to each patient
        doctors = self.molgenis_db.get_with_query('root_hospital_employees', query='function_description==dc')
        for patient in patients_visiting:
            first_name = patient['firstName']
            last_name = patient['lastName']
            doctor = self.get_doctor_for_patient(first_name, last_name, doctors)
            cprint('Patient: [{} {}] will by seen by [dr. {}]'.format(first_name, last_name, doctor['lastName']),
                   'magenta')

        patients_in_db = self.molgenis_db.get_total('root_hospital_patients')

        cprint('Day has ended. Number of patients in database: {}'.format(patients_in_db), 'magenta')


def main():
    cprint("# Before starting, configure the molgenis database wrapper.\n", 'blue')

    server = input("Configure API url (default=http://localhost:8080):\n")
    if not server:
        server = 'http://localhost:8080'

    pwd = getpass.getpass(prompt='Configure your password (default=admin):\n')

    if not pwd:
        pwd = 'admin'

    print("demo = MolgenisDatabase({server}, {password})")
    demo = MolgenisDatabase(server, pwd)

    cprint("# Delete the main package to get rid of all data if already imported", 'blue')
    print("demo.delete_package('root')")
    execute = Execute().do_execute()
    if execute:
        try:
            demo.delete_package('root')
        except:
            cprint('Package root cannot be deleted', 'magenta')
        NextStep()

    cprint("""############################################## Hospital Database ##############################################
    # This script demonstrates how the molgenis python api client can be used.
    # 1) Uploading data using upload_zip""", 'blue')

    print("\tdemo.upload_data('very_advanced_data_example.xlsx')")
    execute = Execute().do_execute()
    if execute:
        demo.upload_data('very_advanced_data_example.xlsx')
        NextStep()

    cprint("""
    # Now your data is imported, let's see what we can do with it.
    # The dataset contains information of a fictional hospital. The tables that contain most of the information are:
    # root_hospital_patients and root_hospital_employees
    # Let's first see what doctors we have available in our hospital: \n""", 'blue')
    print('\tsimulation = HospitalSimulation(demo)\n\tsimulation.get_doctors_description()')
    simulation = HospitalSimulation(demo)
    execute = Execute().do_execute()
    if execute:
        simulation.get_doctors_description()
        NextStep()

    cprint("""
    # It's nice that we can view our data, but of course we also want to add data. To demonstrate this, we will simulate
    # a day in our fictional hospital. A random number of patients will come in, a random part of that will be already
    # registered. The rest of the patients are new. We are going to register the new patients and assign doctors for
    # each patient today.\n""", 'blue')

    print("\tsimulation.simulate_day()")
    execute = Execute().do_execute()
    if execute:
        simulation.simulate_day()
        NextStep()

    cprint("\t# Now let's simulate a few more days to get some more patients.\n", 'blue')

    print("""
    goal = 150
    number_of_patients = demo.get_total('root_hospital_patients')
    while number_of_patients < goal:
        simulation.simulate_day()
        number_of_patients = demo.get_total('root_hospital_patients')""")

    execute = Execute().do_execute()
    if execute:
        goal = 150
        number_of_patients = demo.get_total('root_hospital_patients')

        while number_of_patients < goal:
            simulation.simulate_day()
            number_of_patients = demo.get_total('root_hospital_patients')
        NextStep()

    cprint("\t# Now we filled up the database a bit, let's get a list of all patients;\n", 'blue')

    print("\tall_patients = demo.get('root_hospital_patients')")
    execute = Execute().do_execute()
    if execute:
        all_patients = demo.get('root_hospital_patients')
        cprint('\nNumber of patients: {}'.format(len(all_patients)), 'magenta')
        NextStep()

    cprint("""
    # Hé, that's a bit weird. We just ensured we had at least 150 patients and now we get a length of 100.
    # This is because the get endpoint of the API is paginated. There are two ways to fix this:
    # 1) Do a second call to retrieve the rest of the data
    # 2) Increase the num in the get request (maximum = 10000)\n""", 'blue')

    print("\tnum_increased = demo.molgenis_client.get('root_hospital_patients', num=10000)")
    execute = Execute().do_execute()
    if execute:
        num_increased = demo.molgenis_client.get('root_hospital_patients', num=10000)
        cprint('\nNumber of patients (using increased num): {}'.format(len(num_increased)), 'magenta')
        NextStep()

    cprint("\t# When having more than 10000 lines in your table, you need this\n", 'blue')

    print("""
    total = demo.get_total('root_hospital_patients')
    page_size = 100
    num_of_pages = math.ceil(total / page_size)
    list_of_items = []
    for page in range(num_of_pages):
        start = page_size * page
        items = demo.molgenis_client.get('root_hospital_patients', start=start)
        list_of_items += items""")

    execute = Execute().do_execute()
    if execute:
        total = demo.get_total('root_hospital_patients')
        page_size = 100
        num_of_pages = math.ceil(total / page_size)
        list_of_items = []

        for page in range(num_of_pages):
            start = page_size * page
            items = demo.molgenis_client.get('root_hospital_patients', start=start)
            list_of_items += items

        cprint('\nNumber of patients (using paging): {}'.format(len(list_of_items)), 'magenta')
        NextStep()

    cprint("""
    # Now we covered:
    # Login
    # Get values
    # Add values
    # What else can we do?
    # Let's say one of our patients came in today and asked us to update his family's residence to London.\n""", 'blue')

    print("""
    patient_to_change_first_name = 'Percy Ignatius'
    patient_to_change_last_name = 'Weasley'
    patients_to_update = simulation.get_family_of_patient_by_name(patient_to_change_first_name, patient_to_change_last_name)
    for patient in patients_to_update:
        demo.molgenis_client.update_one('root_hospital_patients', patient, 'residence', 'london')
    """)
    execute = Execute().do_execute()
    if execute:
        patient_to_change_first_name = 'Percy Ignatius'
        patient_to_change_last_name = 'Weasley'
        patients_to_update = simulation.get_family_of_patient_by_name(patient_to_change_first_name,
                                                                      patient_to_change_last_name)
        for patient in patients_to_update:
            demo.molgenis_client.update_one('root_hospital_patients', patient, 'residence', 'london')

        cprint("\t# Let's check if that worked:\n", 'blue')
        print("""
    check = demo.molgenis_client.get('root_hospital_patients', q='id=in=({})'.format(','.join(patients_to_update)),
                                         attributes='id,firstName,lastName,residence')
    for patient in check:
        print('{} {} ({}) is now living in {}'.format(patient['firstName'], patient['lastName'], patient['id'],
                                                          patient['residence']['label']))""")
        check = demo.molgenis_client.get('root_hospital_patients', q='id=in=({})'.format(','.join(patients_to_update)),
                                         attributes='id,firstName,lastName,residence')
        for patient in check:
            cprint('{} {} ({}) is now living in {}'.format(patient['firstName'], patient['lastName'], patient['id'],
                                                           patient['residence']['label']), 'magenta')
        NextStep()

    cprint("""
    # Cool! Now we get to the last part of this tutorial: deleting data.
    #
    # Doctor Gregory House gets fired today. We want to delete him from the employee table.\n""", 'blue')

    print("""
    patient_in_db = demo.get_with_query('root_hospital_employees', 'firstName=="Gregory";lastName=="House"')[0]['id']
    demo.molgenis_client.delete_list('root_hospital_employees', [patient_in_db])""")

    execute = Execute().do_execute()
    if execute:
        employee_in_db = demo.get_with_query('root_hospital_employees', 'firstName=="Gregory";lastName=="House"')[0][
            'id']
        demo.molgenis_client.delete_list('root_hospital_employees', [employee_in_db])
        print('simulation.get_doctors_description()')
        simulation.get_doctors_description()
        cprint("\t# He's gone!", 'blue')
        NextStep()

    cprint("""
    # Always make sure you logout when you're done\n""", 'blue')

    print("\tdemo.molgenis_client.logout()")
    demo.molgenis_client.logout()
    NextStep()

    cprint("""############################################## Tips and Tricks ##############################################
    # 1) For the fastest scripts, do as little REST calls as possible.
    # 2) Beware! When your table will potentially will be bigger than 10000 lines, use the num and start parameter
    #    of the get in combination with retrieving the total number of lines to get all your data.
    # 3) List comprehensions are faster than regular lines of code
    # 4) If you need to combine tables try to expand attributes rather than combining them in the code
    # 5) If still you have to combine tables, use pandas
    # 6) Be aware that the client by default will return the data only, use the raw=True option to retrieve
    #    the metadata and total number of rows.
    # 7) When you're using PyCharm, use the Python Console if you want to test things quickly""", 'green')


if __name__ == '__main__':
    main()
