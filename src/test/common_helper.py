# pylint: disable=no-self-use,unused-argument
import json
import os
from base64 import standard_b64encode
from copy import deepcopy
from typing import Tuple

from helperFunctions.data_conversion import normalize_compare_id
from helperFunctions.fileSystem import get_test_data_dir
from intercom.common_mongo_binding import InterComMongoInterface
from objects.file import FileObject
from objects.firmware import Firmware
from storage.db_interface_common import MongoInterfaceCommon
from storage.db_interface_compare import FactCompareException
from storage.mongo_interface import MongoInterface


class CommonDbInterfaceMock(MongoInterfaceCommon):

    def __init__(self):
        pass

    def retrieve_analysis(self, sanitized_dict, analysis_filter=None):
        return {}


def create_test_firmware(
        device_class='Router', device_name='test_router', vendor='test_vendor', bin_path='container/test.zip',
        all_files_included_set=False, version='0.1') -> Tuple[Firmware, FileObject]:
    root_fo = FileObject(file_path=os.path.join(get_test_data_dir(), bin_path), is_root=True)
    fw = Firmware(device_name=device_name, device_class=device_class, vendor=vendor, version=version,
                  release_date='1970-01-01', uid=root_fo.get_uid())
    root_fo.processed_analysis = {
        'dummy': {'summary': ['sum a', 'fw exclusive sum a'], 'content': 'abcd'},
        'unpacker': {'plugin_used': 'used_unpack_plugin'},
        'file_type': {'mime': 'test_type', 'full': 'Not a PE file'}
    }

    if all_files_included_set:
        root_fo.list_of_all_included_files = list(root_fo.files_included)
        root_fo.list_of_all_included_files.append(root_fo.get_uid())
    return fw, root_fo


def create_test_file_object(bin_path='get_files_test/testfile1'):
    fo = FileObject(file_path=os.path.join(get_test_data_dir(), bin_path))
    processed_analysis = {
        'dummy': {'summary': ['sum a', 'file exclusive sum b'], 'content': 'file abcd'},
        'file_type': {'full': 'Not a PE file'},
        'unpacker': {'file_system_flag': False, 'plugin_used': 'unpacker_name'}
    }
    fo.processed_analysis.update(processed_analysis)
    fo.virtual_file_path = fo.get_virtual_file_paths()
    return fo


TEST_FW, TEST_ROOT_FO = create_test_firmware(device_class='test class', device_name='test device', vendor='test vendor')
TEST_FW_2, TEST_ROOT_FO_2 = create_test_firmware(
    device_class='test_class', device_name='test_firmware_2', vendor='test vendor', bin_path='container/test.7z')
TEST_TEXT_FILE = create_test_file_object()


class MockFileObject:

    def __init__(self, binary=b'test string', file_path='/bin/ls'):
        self.binary = binary
        self.file_path = file_path
        self.processed_analysis = {'file_type': {'mime': 'application/x-executable'}}


class DatabaseMock:  # pylint: disable=too-many-public-methods
    fw_uid = TEST_FW.uid
    fo_uid = TEST_TEXT_FILE.get_uid()
    fw2_uid = TEST_FW_2.uid

    def __init__(self, config=None):
        self.tasks = []
        self.locks = []

    def shutdown(self):
        pass

    def update_view(self, file_name, content):
        pass

    def get_fo_data_for_uid_list(self, uid_list, only_firmwares=False):
        result = []
        for uid in uid_list:
            if uid in [TEST_FW.get_uid(), 'test_uid']:
                result.append({'file_name': 'test_fw'})
            elif uid == TEST_TEXT_FILE.get_uid() and not only_firmwares:
                result.append({'file_name': 'test_fo'})
        return result

    def get_meta_list(self, firmware_list):
        fw_entry = ('test_fw_uid', 'test firmware', 'unpacker')
        fo_entry = ('test_fo_uid', 'test file object', 'unpacker')
        result = []
        for entry in firmware_list:
            if entry['file_name'] == 'test_fw':
                result.append(fw_entry)
            if entry['file_name'] == 'test_fo':
                result.append(fo_entry)
        return result

    def get_meta_list_from_id_list(self, uid_list, only_firmwares=False):
        fw_entry = ('test_fw_uid', 'test firmware', {'unpacker': 'unpacker-tag'})
        fo_entry = ('test_fo_uid', 'test file object', {'unpacker': 'unpacker-tag'})
        result = []
        for uid in uid_list:
            if uid == TEST_FW.firmware_id:
                result.append(fw_entry)
            if uid == TEST_TEXT_FILE.get_uid() and not only_firmwares:
                result.append(fo_entry)
        return result

    def get_number_of_total_matches(self, *_):
        return 10

    def get_object(self, uid, analysis_filter=None):
        if uid == TEST_ROOT_FO.get_uid():
            result = deepcopy(TEST_ROOT_FO)
            result.processed_analysis = {
                'file_type': {'mime': 'application/octet-stream', 'full': 'test text'},
                'mandatory_plugin': 'mandatory result',
                'optional_plugin': 'optional result'
            }
            return result
        if uid == TEST_TEXT_FILE.get_uid():
            result = deepcopy(TEST_TEXT_FILE)
            result.processed_analysis = {
                'file_type': {'mime': 'text/plain', 'full': 'plain text'}
            }
            return result
        if uid == self.fw2_uid:
            result = deepcopy(TEST_ROOT_FO_2)
            result.processed_analysis = {
                'file_type': {'mime': 'filesystem/cramfs', 'full': 'test text'},
                'mandatory_plugin': 'mandatory result',
                'optional_plugin': 'optional result'
            }
            result.release_date = '2000-01-01'
            return result
        return None

    def get_hid(self, uid, root_uid=None):
        return 'TEST_FW_HID'

    def get_device_class_list(self):
        return ['test class']

    def page_compare_results(self):
        return list()

    def get_vendor_list(self):
        return ['test vendor']

    def get_device_name_dict(self):
        return {'test class': {'test vendor': ['test device']}}

    def compare_result_is_in_db(self, uid_list):
        if uid_list == normalize_compare_id(';'.join([TEST_FW.uid, TEST_TEXT_FILE.uid])):
            return True
        return False

    def get_compare_result(self, compare_id):
        if compare_id == normalize_compare_id(';'.join([TEST_FW.uid, TEST_FW_2.uid])):
            return {'this_is': 'a_compare_result',
                    'general': {'hid': {TEST_FW.uid: 'foo', TEST_TEXT_FILE.uid: 'bar'}}}
        if compare_id == normalize_compare_id(';'.join([TEST_FW.uid, TEST_TEXT_FILE.uid])):
            return {'this_is': 'a_compare_result'}
        return 'generic error'

    def object_exists(self, uid):
        if uid in [self.fw_uid, self.fo_uid, self.fw2_uid]:
            return True
        if uid == 'error':
            return True
        return False

    def check_objects_exist(self, compare_id):
        if compare_id == normalize_compare_id(';'.join([TEST_FW_2.uid, TEST_FW.uid])):
            return None
        if compare_id == normalize_compare_id(';'.join([TEST_TEXT_FILE.uid, TEST_FW.uid])):
            return None
        raise FactCompareException('bla')

    def all_uids_found_in_database(self, uid_list):
        return True

    def add_comment_to_object(self, uid, comment, author, time):
        TEST_ROOT_FO.comments.append(
            {'time': str(time), 'author': author, 'comment': comment}
        )

    def get_data_for_nice_list(self, input_data, root_uid):
        return []

    @staticmethod
    def create_analysis_structure():
        return ''

    def generic_search(self, query, skip=0, limit=0, only_fo_parent_firmware=False):
        result = []
        if isinstance(query, dict):
            query = json.dumps(query)
        if TEST_FW.firmware_id in query or query == '{}':
            result.append(TEST_FW.firmware_id)
        if self.fo_uid in query:
            if not only_fo_parent_firmware:
                result.append(self.fo_uid)
            else:
                if self.fw_uid not in result:
                    result.append(TEST_FW.firmware_id)
        return result

    def add_analysis_task(self, task):
        self.tasks.append(task)

    def add_re_analyze_task(self, task, unpack=True):
        self.tasks.append(task)

    def add_compare_task(self, task, force=None):
        self.tasks.append((task, force))

    def get_available_analysis_plugins(self):
        return {
            'default_plugin': ('default plugin description', False, {'default': True}),
            'mandatory_plugin': ('mandatory plugin description', True, {'default': False}),
            'optional_plugin': ('optional plugin description', False, {'default': False}),
            'file_type': ('file_type plugin', False, {'default': False})}

    def get_binary_and_filename(self, uid):
        if uid == TEST_FW.get_uid():
            return TEST_FW.binary, TEST_FW.file_name
        if uid == TEST_TEXT_FILE.get_uid():
            return TEST_TEXT_FILE.binary, TEST_TEXT_FILE.file_name
        return None

    def get_repacked_binary_and_file_name(self, uid):
        if uid == TEST_FW.get_uid():
            return TEST_FW.binary, '{}.tar.gz'.format(TEST_FW.file_name)
        return None

    def add_binary_search_request(self, yara_rule_binary, firmware_uid=None):
        if yara_rule_binary == b'invalid_rule':
            return 'error: invalid rule'
        return 'some_id'

    def get_binary_search_result(self, uid):
        if uid == 'some_id':
            return {'test_rule': ['test_uid']}, b'some yara rule'
        return None, None

    def get_statistic(self, identifier):
        statistics = {
            'number_of_firmwares': 1,
            'number_of_unique_files': 0,
            'total_firmware_size': 10,
            'total_file_size': 20,
            'average_firmware_size': 10,
            'average_file_size': 20,
            'benchmark': 61
        }
        if identifier == 'general':
            return statistics
        return None

    def get_complete_object_including_all_summaries(self, uid):
        if uid == TEST_FW.uid:
            return TEST_FW
        raise Exception('UID not found: {}'.format(uid))

    def rest_get_firmware_uids(self, offset, limit, query=None, recursive=False):
        if (offset != 0) or (limit != 0):
            return []
        return [TEST_FW.uid, ]

    def rest_get_file_object_uids(self, offset, limit, query=None):
        if (offset != 0) or (limit != 0):
            return []
        return [TEST_TEXT_FILE.uid, ]

    def get_firmware(self, uid, analysis_filter=None):
        return self.get_object(uid, analysis_filter)

    def get_file_object(self, uid, analysis_filter=None):
        return self.get_object(uid, analysis_filter)

    def search_cve_summaries_for(self, keyword):
        return [{'_id': 'CVE-2012-0002'}]

    def get_all_ssdeep_hashes(self):
        return [
            {'_id': '3', 'processed_analysis': {'file_hashes': {
                'ssdeep': '384:aztrofSbs/7qkBYbplFPEW5d8aODW9EyGqgm/nZuxpIdQ1s4JtUn:Urofgs/uK2lF8W5dxWyGS/AxpIws'}}},
            {'_id': '4', 'processed_analysis': {'file_hashes': {
                'ssdeep': '384:aztrofSbs/7qkBYbplFPEW5d8aODW9EyGqgm/nZuxpIdQ1s4JwT:Urofgs/uK2lF8W5dxWyGS/AxpIwA'}}}
        ]

    def get_other_versions_of_firmware(self, fo):
        return []

    def get_view(self, name):
        if name == 'plugin_1':
            return b'<plugin 1 view>'
        return None

    def is_firmware(self, uid):
        return uid == 'uid_in_db'

    def get_file_name(self, uid):
        if uid == 'deadbeef00000000000000000000000000000000000000000000000000000000_123':
            return 'test_name'
        return None

    def set_unpacking_lock(self, uid):
        self.locks.append(uid)

    def check_unpacking_lock(self, uid):
        return uid in self.locks

    def drop_unpacking_locks(self):
        self.locks = []

    def get_specific_fields_of_db_entry(self, uid, field_dict):
        return None  # TODO


def fake_exit(self, *args):
    pass


def get_database_names(config):
    databases = ['{}_{}'.format(config.get('data_storage', 'intercom_database_prefix'), intercom_db)
                 for intercom_db in InterComMongoInterface.INTERCOM_CONNECTION_TYPES]
    databases.extend([config.get('data_storage', 'main_database'), config.get(
        'data_storage', 'view_storage'), config.get('data_storage', 'statistic_database')])
    return databases


def clean_test_database(config, list_of_test_databases):
    db = MongoInterface(config=config)
    try:
        for database_name in list_of_test_databases:
            db.client.drop_database(database_name)
    except Exception:
        pass
    db.shutdown()


def get_firmware_for_rest_upload_test():
    testfile_path = os.path.join(get_test_data_dir(), 'container/test.zip')
    with open(testfile_path, 'rb') as fp:
        file_content = fp.read()
    data = {
        'binary': standard_b64encode(file_content).decode(),
        'file_name': 'test.zip',
        'device_name': 'test_device',
        'device_part': 'test_part',
        'device_class': 'test_class',
        'version': '1.0',
        'vendor': 'test_vendor',
        'release_date': '01.01.1970',
        'tags': '',
        'requested_analysis_systems': ['software_components']
    }
    return data
