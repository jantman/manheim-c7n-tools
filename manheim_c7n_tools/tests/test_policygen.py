# Copyright 2017-2019 Manheim / Cox Automotive
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mock import patch, call, mock_open, DEFAULT, Mock, PropertyMock
import pytest
import os
from freezegun import freeze_time

import manheim_c7n_tools.policygen as policygen
from manheim_c7n_tools.config import ManheimConfig


class TestStripDoc(object):

    def test_strip_doc(self):
        """
        Testing
        the code to strip
        whitespace from
        docblocks.
        """

        expected = 'Testing the code to strip whitespace from docblocks.'
        assert policygen.strip_doc(self.test_strip_doc) == expected


class TestInit(object):

    def test_init(self):
        m_conf = Mock()
        type(m_conf).account_name = PropertyMock(return_value='myAccount')
        type(m_conf).account_id = PropertyMock(return_value=1234567890)
        cls = policygen.PolicyGen(m_conf)
        assert cls._config == m_conf


class PolicyGenTester(object):

    def setup(self):
        self.m_conf = Mock(spec_set=ManheimConfig)
        type(self.m_conf).regions = PropertyMock(
            return_value=['region1', 'region2', 'region3']
        )
        type(self.m_conf).output_s3_bucket_name = PropertyMock(
            return_value='BktName'
        )
        type(self.m_conf).custodian_log_group = PropertyMock(
            return_value='LogGroup'
        )
        type(self.m_conf).dead_letter_queue_arn = PropertyMock(
            return_value='Dlq_%%AWS_REGION%%_Arn'
        )
        type(self.m_conf).role_arn = PropertyMock(
            return_value='RoleArn'
        )
        type(self.m_conf).mailer_config = PropertyMock(
            return_value={'queue_url': 'MailerUrl'}
        )
        type(self.m_conf).account_name = PropertyMock(return_value='myAccount')
        type(self.m_conf).account_id = PropertyMock(return_value=1234567890)
        self.m_conf.list_accounts.return_value = ['myAccount', 'otherAccount']
        type(self.m_conf).config_path = PropertyMock(
            return_value='/tmp/conf.yml'
        )
        type(self.m_conf).cleanup_notify = PropertyMock(
            return_value=['me@example.com', 'foo']
        )
        self.cls = policygen.PolicyGen(self.m_conf)


class TestApplyDefaults(PolicyGenTester):

    def test_apply_defaults(self):
        defaults = {
            'mode': {'type': 'periodic', 'schedule': 'foo'},
            'actions': [
                {
                    'type': 'notify',
                    'questions_email': 'qemail',
                    'questions_slack': 'qslack',
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    },
                    'to': [
                        'resource-owner',
                        'me@example.com'
                    ],
                    'owner_absent_contact': [
                        'someone@example.com'
                    ]
                }
            ]
        }
        policy = {
            'name': 'foo',
            'comments': 'my comments',
            'resource': 'bar',
            'filters': [
                {'type': 'baz', 'something': 'else'}
            ],
            'actions': [
                'suspend',
                {'type': 'notify', 'violation_desc': 'vdesc'}
            ]
        }
        expected = {
            'name': 'foo',
            'comments': 'my comments',
            'resource': 'bar',
            'filters': [
                {'type': 'baz', 'something': 'else'}
            ],
            'mode': {
                'type': 'periodic',
                'schedule': 'foo',
                'tags': {'Component': 'foo'}
            },
            'actions': [
                'suspend',
                {
                    'type': 'notify',
                    'violation_desc': 'vdesc',
                    'questions_email': 'qemail',
                    'questions_slack': 'qslack',
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    },
                    'to': [
                        'resource-owner',
                        'me@example.com'
                    ],
                    'owner_absent_contact': [
                        'someone@example.com'
                    ]
                }
            ]
        }
        with patch(
            'manheim_c7n_tools.policygen.PolicyGen._add_always_notify',
            autospec=True
        ) as m:
            m.side_effect = lambda _, x: {'foo': 'bar'}
            res = self.cls._apply_defaults(defaults, policy)
        assert res == {'foo': 'bar'}
        assert m.mock_calls == [call(self.cls, expected)]

    def test_apply_defaults_implicit_mode(self):
        defaults = {
            'mode': {'type': 'periodic', 'schedule': 'foo'},
            'actions': [
                {
                    'type': 'notify',
                    'questions_email': 'qemail',
                    'questions_slack': 'qslack',
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    },
                    'to': [
                        'resource-owner',
                        'me@example.com'
                    ],
                    'owner_absent_contact': [
                        'someone@example.com'
                    ]
                }
            ]
        }
        policy = {
            'name': 'foo',
            'comments': 'my comments',
            'resource': 'bar',
            'filters': [
                {'type': 'baz', 'something': 'else'}
            ],
            'actions': [
                'suspend',
                {
                    'type': 'notify',
                    'violation_desc': 'vdesc',
                    'owner_absent_contact': [
                        'foo@bar.com'
                    ]
                }
            ],
            'mode': {'schedule': 'bar'}
        }
        expected = {
            'name': 'foo',
            'comments': 'my comments',
            'resource': 'bar',
            'filters': [
                {'type': 'baz', 'something': 'else'}
            ],
            'mode': {
                'type': 'periodic',
                'schedule': 'bar',
                'tags': {'Component': 'foo'}
            },
            'actions': [
                'suspend',
                {
                    'type': 'notify',
                    'violation_desc': 'vdesc',
                    'questions_email': 'qemail',
                    'questions_slack': 'qslack',
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    },
                    'to': [
                        'resource-owner',
                        'me@example.com'
                    ],
                    'owner_absent_contact': [
                        'foo@bar.com'
                    ]
                }
            ]
        }
        with patch(
            'manheim_c7n_tools.policygen.PolicyGen._add_always_notify',
            autospec=True
        ) as m:
            m.side_effect = lambda _, x: {'foo': 'bar'}
            res = self.cls._apply_defaults(defaults, policy)
        assert res == {'foo': 'bar'}
        assert m.mock_calls == [call(self.cls, expected)]

    def test_apply_defaults_tags(self):
        defaults = {
            'mode': {
                'type': 'periodic',
                'schedule': 'foo',
                'tags': {'Project': 'cloud-custodian'}
            },
            'actions': [
                {
                    'type': 'notify',
                    'questions_email': 'qemail',
                    'questions_slack': 'qslack',
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    },
                    'to': [
                        'resource-owner',
                        'me@example.com'
                    ]
                }
            ]
        }
        policy = {
            'name': 'foo',
            'comments': 'my comments',
            'resource': 'bar',
            'filters': [
                {'type': 'baz', 'something': 'else'}
            ],
            'actions': [
                'suspend',
                {'type': 'notify', 'violation_desc': 'vdesc'}
            ]
        }
        expected = {
            'name': 'foo',
            'comments': 'my comments',
            'resource': 'bar',
            'filters': [
                {'type': 'baz', 'something': 'else'}
            ],
            'mode': {
                'type': 'periodic',
                'schedule': 'foo',
                'tags': {'Component': 'foo', 'Project': 'cloud-custodian'}
            },
            'actions': [
                'suspend',
                {
                    'type': 'notify',
                    'violation_desc': 'vdesc',
                    'questions_email': 'qemail',
                    'questions_slack': 'qslack',
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    },
                    'to': [
                        'resource-owner',
                        'me@example.com'
                    ]
                }
            ]
        }
        with patch(
            'manheim_c7n_tools.policygen.PolicyGen._add_always_notify',
            autospec=True
        ) as m:
            m.side_effect = lambda _, x: {'foo': 'bar'}
            res = self.cls._apply_defaults(defaults, policy)
        assert res == {'foo': 'bar'}
        assert m.mock_calls == [call(self.cls, expected)]

    def test_apply_defaults_not_periodic(self):
        defaults = {
            'mode': {
                'type': 'periodic',
                'schedule': 'rate(1 day)',
                'tags': {'foo': 'bar', 'baz': 'blam'}
            },
            'actions': [
                {
                    'type': 'notify',
                    'questions_email': 'qemail',
                    'questions_slack': 'qslack',
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    },
                    'to': [
                        'resource-owner',
                        'me@example.com'
                    ]
                }
            ]
        }
        policy = {
            'name': 'foo',
            'comments': 'my comments',
            'resource': 'bar',
            'filters': [
                {'type': 'baz', 'something': 'else'}
            ],
            'actions': [
                'suspend',
                {'type': 'notify', 'violation_desc': 'vdesc'}
            ],
            'mode': {'type': 'bar', 'schedule': 'foo'},
        }
        expected = {
            'name': 'foo',
            'comments': 'my comments',
            'resource': 'bar',
            'filters': [
                {'type': 'baz', 'something': 'else'}
            ],
            'mode': {
                'type': 'bar',
                'schedule': 'foo'
            },
            'actions': [
                'suspend',
                {
                    'type': 'notify',
                    'violation_desc': 'vdesc',
                    'questions_email': 'qemail',
                    'questions_slack': 'qslack',
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    },
                    'to': [
                        'resource-owner',
                        'me@example.com'
                    ]
                }
            ]
        }
        with patch(
            'manheim_c7n_tools.policygen.PolicyGen._add_always_notify',
            autospec=True
        ) as m:
            m.side_effect = lambda _, x: {'foo': 'bar'}
            res = self.cls._apply_defaults(defaults, policy)
        assert res == {'foo': 'bar'}
        assert m.mock_calls == [call(self.cls, expected)]

    def test_apply_defaults_not_periodic_with_tags(self):
        defaults = {
            'mode': {
                'type': 'periodic',
                'schedule': 'rate(1 day)',
                'tags': {'foo': 'bar', 'baz': 'blam'}
            },
            'actions': [
                {
                    'type': 'notify',
                    'questions_email': 'qemail',
                    'questions_slack': 'qslack',
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    },
                    'to': [
                        'resource-owner',
                        'me@example.com'
                    ]
                }
            ]
        }
        policy = {
            'name': 'foo',
            'comments': 'my comments',
            'resource': 'bar',
            'filters': [
                {'type': 'baz', 'something': 'else'}
            ],
            'actions': [
                'suspend',
                {'type': 'notify', 'violation_desc': 'vdesc'}
            ],
            'mode': {'type': 'bar', 'schedule': 'foo', 'tags': {}},
        }
        expected = {
            'name': 'foo',
            'comments': 'my comments',
            'resource': 'bar',
            'filters': [
                {'type': 'baz', 'something': 'else'}
            ],
            'mode': {
                'type': 'bar',
                'schedule': 'foo',
                'tags': {'foo': 'bar', 'baz': 'blam', 'Component': 'foo'}
            },
            'actions': [
                'suspend',
                {
                    'type': 'notify',
                    'violation_desc': 'vdesc',
                    'questions_email': 'qemail',
                    'questions_slack': 'qslack',
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    },
                    'to': [
                        'resource-owner',
                        'me@example.com'
                    ]
                }
            ]
        }
        with patch(
            'manheim_c7n_tools.policygen.PolicyGen._add_always_notify',
            autospec=True
        ) as m:
            m.side_effect = lambda _, x: {'foo': 'bar'}
            res = self.cls._apply_defaults(defaults, policy)
        assert res == {'foo': 'bar'}
        assert m.mock_calls == [call(self.cls, expected)]

    def test_apply_defaults_merge_call(self):
        with patch(
            'manheim_c7n_tools.policygen.PolicyGen._merge_conf', autospec=True
        ) as m:
            m.return_value = {'mode': {'type': 'foo'}}
            with patch(
                    'manheim_c7n_tools.policygen.PolicyGen._add_always_notify',
                    autospec=True
            ) as m_aan:
                m_aan.side_effect = lambda _, x: {'foo': 'bar'}
                self.cls._apply_defaults({}, {'name': 'pname'})
        assert m.mock_calls == [
            call(self.cls, {}, {'name': 'pname'}, 'pname', [])
        ]
        assert m_aan.mock_calls == [
            call(self.cls, {'mode': {'type': 'foo'}, 'actions': []})
        ]


class TestAddAlwaysNotify(PolicyGenTester):

    def test_not_configured(self):
        original = {
            'actions': []
        }
        assert self.cls._add_always_notify(original) == original

    def test_empty_actions(self):
        type(self.m_conf).always_notify = PropertyMock(
            return_value={
                'to': ['toAddr1', 'toAddr2'],
                'transport': {
                    'queue': 'q',
                    'type': 'sqs'
                }
            }
        )
        original = {
            'actions': []
        }
        expected = {
            'actions': [
                {
                    'type': 'notify',
                    'to': ['toAddr1', 'toAddr2'],
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    }
                }
            ]
        }
        assert self.cls._add_always_notify(original) == expected

    def test_no_notify_action(self):
        type(self.m_conf).always_notify = PropertyMock(
            return_value={
                'to': ['toAddr1', 'toAddr2'],
                'transport': {
                    'queue': 'q',
                    'type': 'sqs'
                }
            }
        )
        original = {
            'actions': [
                'foo',
                {'type': 'bar'}
            ]
        }
        expected = {
            'actions': [
                'foo',
                {'type': 'bar'},
                {
                    'type': 'notify',
                    'to': ['toAddr1', 'toAddr2'],
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    }
                }
            ]
        }
        assert self.cls._add_always_notify(original) == expected

    def test_notify_different_transport(self):
        type(self.m_conf).always_notify = PropertyMock(
            return_value={
                'to': ['toAddr1', 'toAddr2'],
                'transport': {
                    'queue': 'q',
                    'type': 'sqs'
                }
            }
        )
        original = {
            'actions': [
                'foo',
                {'type': 'bar'},
                {
                    'type': 'notify',
                    'to': ['foo'],
                    'transport': {
                        'queue': 'notQ',
                        'type': 'sqs'
                    }
                }
            ]
        }
        expected = {
            'actions': [
                'foo',
                {'type': 'bar'},
                {
                    'type': 'notify',
                    'to': ['foo'],
                    'transport': {
                        'queue': 'notQ',
                        'type': 'sqs'
                    }
                },
                {
                    'type': 'notify',
                    'to': ['toAddr1', 'toAddr2'],
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    }
                }
            ]
        }
        assert self.cls._add_always_notify(original) == expected

    def test_already_present(self):
        type(self.m_conf).always_notify = PropertyMock(
            return_value={
                'to': ['toAddr1', 'toAddr2'],
                'transport': {
                    'queue': 'q',
                    'type': 'sqs'
                }
            }
        )
        original = {
            'actions': [
                'foo',
                {'type': 'bar'},
                {'type': 'notify', 'transport': 'foo'},
                {'type': 'notify', 'to': 'bar'},
                {
                    'type': 'notify',
                    'to': ['toAddr1', 'toAddr2'],
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    }
                },
                {
                    'type': 'notify',
                    'to': ['foo'],
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    }
                }
            ]
        }
        assert self.cls._add_always_notify(original) == original

    def test_right_transport(self):
        type(self.m_conf).always_notify = PropertyMock(
            return_value={
                'to': ['toAddr1', 'toAddr2'],
                'transport': {
                    'queue': 'q',
                    'type': 'sqs'
                }
            }
        )
        original = {
            'actions': [
                'foo',
                {'type': 'bar'},
                {
                    'type': 'notify',
                    'to': ['foo', 'bar'],
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    }
                }
            ]
        }
        expected = {
            'actions': [
                'foo',
                {'type': 'bar'},
                {
                    'type': 'notify',
                    'to': ['foo', 'bar', 'toAddr1', 'toAddr2'],
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    }
                }
            ]
        }
        assert self.cls._add_always_notify(original) == expected

    def test_to_from(self):
        type(self.m_conf).always_notify = PropertyMock(
            return_value={
                'to': ['toAddr1', 'toAddr2'],
                'transport': {
                    'queue': 'q',
                    'type': 'sqs'
                }
            }
        )
        original = {
            'actions': [
                'foo',
                {'type': 'bar'},
                {
                    'type': 'notify',
                    'to_from': ['foo', 'bar'],
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    }
                }
            ]
        }
        expected = {
            'actions': [
                'foo',
                {'type': 'bar'},
                {
                    'type': 'notify',
                    'to': ['toAddr1', 'toAddr2'],
                    'to_from': ['foo', 'bar'],
                    'transport': {
                        'queue': 'q',
                        'type': 'sqs'
                    }
                }
            ]
        }
        assert self.cls._add_always_notify(original) == expected


class TestMergeConf(PolicyGenTester):

    def test_merge_conf_missing(self):
        update = {'foo': 'bar', 'baz': ['blam'], 'blarg': {'a': 'b'}}
        assert self.cls._merge_conf({}, update, 'pname', []) == update

    def test_merge_conf_string(self):
        base = {'foo': 'bar', 'baz': 'blam'}
        update = {'foo': 'newfoo'}
        assert self.cls._merge_conf(base, update, 'pname', []) == {
            'foo': 'newfoo', 'baz': 'blam'
        }

    def test_merge_conf_no_actions(self):
        base = {'actions': [{'foo': 'bar'}, {'baz': 'blam'}], 'blam': 'blarg'}
        update = {'foo': {'bar': 'newbar', 'baz': 'bazvalue'}}
        expected = {
            'foo': {
                'bar': 'newbar',
                'baz': 'bazvalue'
            },
            'blam': 'blarg'
        }
        assert self.cls._merge_conf(base, update, 'pname', []) == expected

    def test_merge_conf_dict(self):
        base = {'foo': {'bar': 'barvalue', 'blam': 'blamvalue'}}
        update = {'foo': {'bar': 'newbar', 'baz': 'bazvalue'}}
        expected = {
            'foo': {
                'bar': 'newbar',
                'baz': 'bazvalue',
                'blam': 'blamvalue'
            }
        }
        assert self.cls._merge_conf(base, update, 'pname', []) == expected

    def test_merge_conf_array(self):
        base = {
            'foo': 'bar',
            'myarr': ['baz', 2, {'type': 'mytype'}]
        }
        update = {
            'baz': 'bazvalue',
            'myarr': ['one']
        }
        expected = {
            'foo': 'bar',
            'baz': 'bazvalue',
            'myarr': ['foo', 'bar', 1]
        }
        with patch(
            'manheim_c7n_tools.policygen.PolicyGen._array_merge', autospec=True
        ) as mock_am:
            mock_am.return_value = ['foo', 'bar', 1]
            res = self.cls._merge_conf(base, update, 'pname', [])
        assert res == expected
        assert mock_am.mock_calls == [call(
            self.cls,
            ['baz', 2, {'type': 'mytype'}],
            ['one'],
            'pname',
            ['myarr']
        )]


class TestArrayMerge(PolicyGenTester):

    def test_not_dict(self):
        base = ['one', 2, ['baz']]
        update = [['baz'], 'three', 4]
        expected = [['baz'], 'three', 4, 'one', 2]
        assert self.cls._array_merge(base, update, 'pname', []) == expected

    def test_dicts(self):
        base = [
            {'type': 'foo', 'bar': 'barvalue', 'extra': 'eval'},
            {'type': 'bar', 'extra': 'eval'},
            'blam',
            'blarg'
        ]
        update = [
            {'type': 'foo', 'bar': 'barupdate', 'baz': 'blam'},
            {'type': 'baz', 'bar': 'bazvalue'},
            {'foo': 'bar'},
            'blam',
            'quux'
        ]
        expected = [
            {'type': 'foo', 'bar': 'barupdate', 'extra': 'eval', 'baz': 'blam'},
            {'type': 'baz', 'bar': 'bazvalue'},
            {'foo': 'bar'},
            'blam',
            'quux',
            'blarg',
            {'type': 'bar', 'extra': 'eval'}
        ]
        assert self.cls._array_merge(base, update, 'pname', []) == expected

    def test_no_add_notification(self):
        # ensure that _array_merge() doesn't add a notify action to policies
        # that don't have one
        base = [
            {'type': 'notify', 'to': ['foo', 'bar']}
        ]
        update = [
            'foo',
            'bar',
            {'type': 'baz', 'blam': 'blarg'}
        ]
        assert self.cls._array_merge(base, update, 'pname', ['actions']) == [
            'foo',
            'bar',
            {'type': 'baz', 'blam': 'blarg'}
        ]

    def test_base_dict_no_type(self):
        base = [{'foo': 'bar'}]
        with pytest.raises(RuntimeError):
            self.cls._array_merge(base, [], 'pname', [])

    def test_base_multiple_type(self):
        base = [
            {'type': 'foo'},
            {'type': 'foo'}
        ]
        with pytest.raises(RuntimeError):
            self.cls._array_merge(base, [], 'pname', [])

    def test_base_not_array(self):
        base = 'foo'
        update = [1, 2]
        with pytest.raises(RuntimeError):
            self.cls._array_merge(base, update, 'pname', [])


class TestWriteFile(PolicyGenTester):

    def test_write(self):
        with patch(
            'manheim_c7n_tools.policygen.open', mock_open(), create=True
        ) as m_open:
            self.cls._write_file('fpath', 'fcontent')
        assert m_open.mock_calls == [
            call('fpath', 'w'),
            call().__enter__(),
            call().write('fcontent'),
            call().__exit__(None, None, None)
        ]


class TestRun(PolicyGenTester):

    def test_simple(self):

        policies = {
            'myAccount': {
                'region1': {
                    'foo': 'bar-myAccount/region1',
                    'baz': 'blam',
                    'myAccount/common': 'c'
                },
                'region2': {
                    'foo': 'bar-myAccount/region2',
                    'baz': 'blam',
                    'myAccount/common': 'c'
                },
                'region3': {
                    'foo': 'bar-myAccount/region3',
                    'baz': 'blam',
                    'myAccount/common': 'c'
                }
            },
            'all_accounts': {
                'region1': {
                    'all_r1': 'region1',
                    'all_common': 'region1'
                },
                'region2': {
                    'all_r2': 'region2',
                    'all_common': 'region2'
                },
                'region3': {
                    'all_r3': 'region3',
                    'all_common': 'region3'
                }
            },
            'otherAccount': {
                'region1': {
                    'foo': 'bar-otherAccount/region1',
                    'baz': 'blam',
                    'otherAccount/common': 'c'
                },
                'region2': {
                    'foo': 'bar-otherAccount/region2',
                    'baz': 'blam',
                    'otherAccount/common': 'c'
                },
                'region3': {
                    'foo': 'bar-otherAccount/region3',
                    'baz': 'blam',
                    'otherAccount/common': 'c'
                }
            }
        }

        def se_read_pol_dir(_, dirname):
            return policies[dirname]

        with patch.multiple(
            'manheim_c7n_tools.policygen.PolicyGen',
            autospec=True,
            _read_policy_directory=DEFAULT,
            _generate_configs=DEFAULT,
            _policy_rst=DEFAULT,
            _write_file=DEFAULT,
            _regions_rst=DEFAULT,
            _read_file_yaml=DEFAULT
        ) as mocks:
            mocks['_read_policy_directory'].side_effect = se_read_pol_dir
            mocks['_policy_rst'].return_value = 'polMD'
            mocks['_regions_rst'].return_value = 'regionsRST'
            mocks['_read_file_yaml'].return_value = 'DEFAULTS'
            self.cls.run()
        assert mocks['_read_policy_directory'].mock_calls == [
            call(self.cls, 'all_accounts'),
            call(self.cls, 'myAccount'),
            call(self.cls, 'otherAccount')
        ]
        assert mocks['_generate_configs'].mock_calls == [
            call(
                self.cls,
                {
                    'foo': 'bar-myAccount/region1',
                    'baz': 'blam',
                    'myAccount/common': 'c',
                    'all_r1': 'region1',
                    'all_common': 'region1'
                },
                'DEFAULTS',
                'region1'
            ),
            call(
                self.cls,
                {
                    'foo': 'bar-myAccount/region2',
                    'baz': 'blam',
                    'myAccount/common': 'c',
                    'all_r2': 'region2',
                    'all_common': 'region2'
                },
                'DEFAULTS',
                'region2'
            ),
            call(
                self.cls,
                {
                    'foo': 'bar-myAccount/region3',
                    'baz': 'blam',
                    'myAccount/common': 'c',
                    'all_r3': 'region3',
                    'all_common': 'region3'
                },
                'DEFAULTS',
                'region3'
            )
        ]
        assert mocks['_policy_rst'].mock_calls == [
            call(
                self.cls,
                {
                    'myAccount': {
                        'region1': {
                            'foo': 'bar-myAccount/region1',
                            'baz': 'blam',
                            'myAccount/common': 'c',
                            'all_r1': 'region1',
                            'all_common': 'region1'
                        },
                        'region2': {
                            'foo': 'bar-myAccount/region2',
                            'baz': 'blam',
                            'myAccount/common': 'c',
                            'all_r2': 'region2',
                            'all_common': 'region2'
                        },
                        'region3': {
                            'foo': 'bar-myAccount/region3',
                            'baz': 'blam',
                            'myAccount/common': 'c',
                            'all_r3': 'region3',
                            'all_common': 'region3'
                        }
                    },
                    'otherAccount': {
                        'region1': {
                            'foo': 'bar-otherAccount/region1',
                            'baz': 'blam',
                            'otherAccount/common': 'c',
                            'all_r1': 'region1',
                            'all_common': 'region1'
                        },
                        'region2': {
                            'foo': 'bar-otherAccount/region2',
                            'baz': 'blam',
                            'otherAccount/common': 'c',
                            'all_r2': 'region2',
                            'all_common': 'region2'
                        },
                        'region3': {
                            'foo': 'bar-otherAccount/region3',
                            'baz': 'blam',
                            'otherAccount/common': 'c',
                            'all_r3': 'region3',
                            'all_common': 'region3'
                        }
                    }
                }
            )
        ]
        assert mocks['_regions_rst'].mock_calls == [call(self.cls)]
        assert mocks['_write_file'].mock_calls == [
            call(self.cls, 'policies.rst', 'polMD'),
            call(self.cls, 'regions.rst', 'regionsRST')
        ]
        assert mocks['_read_file_yaml'].mock_calls == [
            call(self.cls, 'policies/defaults.yml')
        ]


class TestReadPolicyDirectory(PolicyGenTester):

    def test_simple(self):

        def se_read_policies(_, rname):
            d = {
                'foo': 'bar-%s' % rname,
                'baz': 'blam'
            }
            if rname == 'foo/common':
                d['foo/common'] = 'c'
            return d

        with patch.multiple(
            'manheim_c7n_tools.policygen.PolicyGen',
            autospec=True,
            _read_policies=DEFAULT
        ) as mocks:
            mocks['_read_policies'].side_effect = se_read_policies
            res = self.cls._read_policy_directory('foo')
        assert mocks['_read_policies'].mock_calls == [
            call(self.cls, 'foo/common'),
            call(self.cls, 'foo/region1'),
            call(self.cls, 'foo/region2'),
            call(self.cls, 'foo/region3')
        ]
        assert res == {
            'region1': {
                'foo': 'bar-foo/region1',
                'baz': 'blam',
                'foo/common': 'c'
            },
            'region2': {
                'foo': 'bar-foo/region2',
                'baz': 'blam',
                'foo/common': 'c'
            },
            'region3': {
                'foo': 'bar-foo/region3',
                'baz': 'blam',
                'foo/common': 'c'
            }
        }


class TestGenerateConfigs(PolicyGenTester):

    def test_simple(self):

        def se_apply_defaults(klass, defaults, policy):
            return '%s+defaults' % policy

        policies = {
            'foo': 'bar',
            'baz': 'blam'
        }
        with patch.multiple(
            'manheim_c7n_tools.policygen.PolicyGen',
            autospec=True,
            _apply_defaults=DEFAULT,
            _generate_cleanup_policies=DEFAULT,
            _check_policies=DEFAULT,
            _write_custodian_configs=DEFAULT
        ) as mocks:
            mocks['_apply_defaults'].side_effect = se_apply_defaults
            mocks['_generate_cleanup_policies'].return_value = [
                'cleanup1', 'cleanup2'
            ]
            res = self.cls._generate_configs(policies, 'quux', 'region2')
        assert res == {
            'policies': [
                'blam+defaults',
                'bar+defaults',
                'cleanup1+defaults',
                'cleanup2+defaults'
            ]
        }
        assert mocks['_apply_defaults'].mock_calls == [
            call(self.cls, 'quux', 'blam'),
            call(self.cls, 'quux', 'bar'),
            call(self.cls, 'quux', 'cleanup1'),
            call(self.cls, 'quux', 'cleanup2')
        ]
        assert mocks['_generate_cleanup_policies'].mock_calls == [
            call(self.cls, ['blam+defaults', 'bar+defaults'])
        ]
        exp_policies = {
            'policies': [
                'blam+defaults',
                'bar+defaults',
                'cleanup1+defaults',
                'cleanup2+defaults'
                ]
        }
        assert mocks['_write_custodian_configs'].mock_calls == [
            call(self.cls, exp_policies, 'region2')
        ]
        assert mocks['_check_policies'].mock_calls == [
            call(
                self.cls,
                [
                    'blam+defaults',
                    'bar+defaults',
                    'cleanup1+defaults',
                    'cleanup2+defaults'
                ]
            )
        ]

    def test_no_cleanup(self):
        type(self.m_conf).cleanup_notify = PropertyMock(
            return_value=[]
        )

        def se_apply_defaults(klass, defaults, policy):
            return '%s+defaults' % policy

        policies = {
            'foo': 'bar',
            'baz': 'blam'
        }
        with patch.multiple(
            'manheim_c7n_tools.policygen.PolicyGen',
            autospec=True,
            _apply_defaults=DEFAULT,
            _generate_cleanup_policies=DEFAULT,
            _check_policies=DEFAULT,
            _write_custodian_configs=DEFAULT
        ) as mocks:
            mocks['_apply_defaults'].side_effect = se_apply_defaults
            mocks['_generate_cleanup_policies'].return_value = []
            res = self.cls._generate_configs(policies, 'quux', 'region2')
        assert res == {
            'policies': [
                'blam+defaults',
                'bar+defaults'
            ]
        }
        assert mocks['_apply_defaults'].mock_calls == [
            call(self.cls, 'quux', 'blam'),
            call(self.cls, 'quux', 'bar')
        ]
        assert mocks['_generate_cleanup_policies'].mock_calls == []
        exp_policies = {
            'policies': [
                'blam+defaults',
                'bar+defaults'
            ]
        }
        assert mocks['_write_custodian_configs'].mock_calls == [
            call(self.cls, exp_policies, 'region2')
        ]
        assert mocks['_check_policies'].mock_calls == [
            call(
                self.cls,
                [
                    'blam+defaults',
                    'bar+defaults'
                ]
            )
        ]


class TestWriteCustodianConfigs(PolicyGenTester):

    @patch.dict(
        'os.environ',
        {'POLICYGEN_ENV_foo': 'EVAR', 'Something': 'else'},
        clear=True
    )
    def test_write(self):
        original = {
            'foo': 'bar%%AWS_REGION%%baz',
            'bar': [
                'baz',
                'AWS_REGION',
                '%%AWS_REGION%%',
                'xx%%AWS_REGION%%xx',
                'blam',
                'xx%%BUCKET_NAME%%xx'
            ],
            'baz': {
                'blam': {
                    'blarg%%AWS_REGION%%xx': 'xxx%%AWS_REGION%%xxx'
                }
            }
        }
        with patch(
            'manheim_c7n_tools.policygen.PolicyGen._write_file', autospec=True
        ) as mock_wf:
            with patch(
                'manheim_c7n_tools.policygen.yaml.dump', autospec=True
            ) as mock_dump:
                mock_dump.return_value = \
                    'yaml%%AWS_REGION%%yaml%%BUCKET_NAME%%x%%LOG_GROUP%%x' \
                    '%%DLQ_ARN%%x%%ROLE_ARN%%x%%MAILER_QUEUE_URL%%x' \
                    '%%ACCOUNT_NAME%%x%%ACCOUNT_ID%%xx' \
                    '%%POLICYGEN_ENV_foo%%x'
                self.cls._write_custodian_configs(original, 'region1')
        assert mock_dump.mock_calls == [call(original)]
        assert mock_wf.mock_calls == [
            call(
                self.cls,
                'custodian_region1.yml',
                'yamlregion1yamlBktNamexLogGroupxDlq_region1_ArnxRoleArnx'
                'MailerUrlxmyAccountx1234567890xxEVARx'
            )
        ]


class TestCheckPolicies(PolicyGenTester):

    def test_success(self):
        policies = [
            {'name': 'foo', 'foo': 'bar'},
            {'name': 'baz', 'baz': 'blam'}
        ]
        with patch.multiple(
            'manheim_c7n_tools.policygen.PolicyGen',
            autospec=True,
            _check_policy_marked_for_op_first=DEFAULT
        ) as mocks:
            mocks['_check_policy_marked_for_op_first'].return_value = True
            with patch(
                'manheim_c7n_tools.policygen.logger', autospec=True
            ) as mock_logger:
                self.cls._check_policies(policies)
        assert mocks['_check_policy_marked_for_op_first'].mock_calls == [
            call(self.cls, policies[0]),
            call(self.cls, policies[1])
        ]
        assert mock_logger.mock_calls == [
            call.info('OK: All policies passed sanity/safety checks.')
        ]

    def test_failure(self):
        def se_strip_doc(func):
            return func.name

        policies = [
            {'name': 'foo', 'foo': 'bar'},
            {'name': 'baz', 'baz': 'blam'}
        ]
        with patch.multiple(
            'manheim_c7n_tools.policygen.PolicyGen',
            autospec=True,
            _check_policy_marked_for_op_first=DEFAULT,
        ) as mocks:
            with patch(
                'manheim_c7n_tools.policygen.strip_doc', autospec=True
            ) as mock_sd:
                for x in mocks:
                    setattr(mocks[x], 'name', x)
                mocks['_check_policy_marked_for_op_first'].return_value = False
                mock_sd.side_effect = se_strip_doc
                with patch(
                    'manheim_c7n_tools.policygen.logger', autospec=True
                ) as mock_logger:
                    with pytest.raises(SystemExit) as ex:
                        self.cls._check_policies(policies)
                assert ex.value.args[0] == 1
        assert mocks['_check_policy_marked_for_op_first'].mock_calls == [
            call(self.cls, policies[0]),
            call(self.cls, policies[1])
        ]
        assert mock_logger.mock_calls == [
            call.error('ERROR: Some policies failed sanity/safety checks:'),
            call.error('baz'),
            call.error('\t_check_policy_marked_for_op_first'),
            call.error('foo'),
            call.error('\t_check_policy_marked_for_op_first')
        ]


class TestCheckPolicyMarkedForOpFirst(PolicyGenTester):

    def test_no_filters(self):
        policy = {'name': 'foo', 'actions': ['mark']}
        assert self.cls._check_policy_marked_for_op_first(policy) is True

    def test_no_marked_for_op(self):
        policy = {
            'name': 'foo',
            'actions': ['mark'],
            'filters': [
                'alive',
                {'tag:foo': 'present'}
            ]
        }
        assert self.cls._check_policy_marked_for_op_first(policy) is True

    def test_marked_for_op_first(self):
        policy = {
            'name': 'foo',
            'actions': ['mark'],
            'filters': [
                {
                    'type': 'marked-for-op',
                    'tag': 'foo',
                    'op': 'bar'
                },
                'alive',
                {'tag:foo': 'present'}
            ]
        }
        assert self.cls._check_policy_marked_for_op_first(policy) is True

    def test_marked_for_op_not_first(self):
        policy = {
            'name': 'foo',
            'actions': ['mark'],
            'filters': [
                'alive',
                {'tag:foo': 'present'},
                {
                    'type': 'marked-for-op',
                    'tag': 'foo',
                    'op': 'bar'
                }
            ]
        }
        assert self.cls._check_policy_marked_for_op_first(policy) is False

    def test_marked_for_op_nested(self):
        policy = {
            'name': 'foo',
            'actions': ['mark'],
            'filters': [
                {
                    'or': [
                        {'tag:foo': 'present'},
                        {
                            'type': 'marked-for-op',
                            'tag': 'foo',
                            'op': 'bar'
                        },
                        'alive'
                    ]
                }
            ]
        }
        assert self.cls._check_policy_marked_for_op_first(policy) is False


class TestCheckPolicyMarkButNoTagFilter(PolicyGenTester):

    def test_no_filters(self):
        policy = {'name': 'foo', 'actions': ['mark']}
        assert self.cls._check_policy_mark_but_no_tag_filter(policy) is True

    def test_no_actions(self):
        policy = {'name': 'foo', 'filters': ['foo']}
        assert self.cls._check_policy_mark_but_no_tag_filter(policy) is True

    def test_no_mark_actions(self):
        policy = {
            'name': 'foo',
            'filters': ['foo'],
            'actions': [
                'stop',
                {'type': 'foo'},
                {'foo': 'bar'}
            ]
        }
        assert self.cls._check_policy_mark_but_no_tag_filter(policy) is True

    def test_one_mark_action_ok(self):
        policy = {
            'name': 'foo',
            'actions': [
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-mytag',
                    'op': 'stop',
                    'message': 'foo-mark {op}@{action_date}',
                    'days': 7
                }
            ],
            'filters': [
                {
                    'type': 'value',
                    'key': 'Instances',
                    'value_type': 'size',
                    'op': 'less-than',
                    'value': 1
                },
                {
                    'tag:c7n-mytag': 'absent'
                }
            ]
        }
        assert self.cls._check_policy_mark_but_no_tag_filter(policy) is True

    def test_two_mark_actions_ok(self):
        policy = {
            'name': 'foo',
            'actions': [
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-mytag',
                    'op': 'stop',
                    'message': 'foo-mark {op}@{action_date}',
                    'days': 7
                },
                'stop',
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-foobar',
                    'op': 'delete',
                    'message': 'foobar-mark {op}@{action_date}',
                    'days': 14
                }
            ],
            'filters': [
                {
                    'type': 'value',
                    'key': 'Instances',
                    'value_type': 'size',
                    'op': 'less-than',
                    'value': 1
                },
                {
                    'tag:c7n-mytag': 'absent'
                },
                {
                    'tag:c7n-foobar': 'absent'
                }
            ]
        }
        assert self.cls._check_policy_mark_but_no_tag_filter(policy) is True

    def test_one_mark_action_no_filter(self):
        policy = {
            'name': 'foo',
            'actions': [
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-mytag',
                    'op': 'stop',
                    'message': 'foo-mark {op}@{action_date}',
                    'days': 7
                }
            ],
            'filters': [
                {
                    'tag:c7n-NOTmytag': 'absent'
                },
                {
                    'type': 'value',
                    'key': 'Instances',
                    'value_type': 'size',
                    'op': 'less-than',
                    'value': 1
                }
            ]
        }
        assert self.cls._check_policy_mark_but_no_tag_filter(policy) is False

    def test_two_mark_actions_one_filter(self):
        policy = {
            'name': 'foo',
            'actions': [
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-mytag',
                    'op': 'stop',
                    'message': 'foo-mark {op}@{action_date}',
                    'days': 7
                },
                'stop',
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-foobar',
                    'op': 'delete',
                    'message': 'foobar-mark {op}@{action_date}',
                    'days': 14
                }
            ],
            'filters': [
                {
                    'type': 'value',
                    'key': 'Instances',
                    'value_type': 'size',
                    'op': 'less-than',
                    'value': 1
                },
                {
                    'tag:c7n-NOTmytag': 'absent'
                },
                {
                    'tag:c7n-foobar': 'absent'
                }
            ]
        }
        assert self.cls._check_policy_mark_but_no_tag_filter(policy) is False

    def test_two_mark_actions_no_filters(self):
        policy = {
            'name': 'foo',
            'actions': [
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-mytag',
                    'op': 'stop',
                    'message': 'foo-mark {op}@{action_date}',
                    'days': 7
                },
                'stop',
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-foobar',
                    'op': 'delete',
                    'message': 'foobar-mark {op}@{action_date}',
                    'days': 14
                }
            ],
            'filters': [
                {
                    'type': 'value',
                    'key': 'Instances',
                    'value_type': 'size',
                    'op': 'less-than',
                    'value': 1
                },
                {
                    'tag:c7n-NOTmytag': 'absent'
                }
            ]
        }
        assert self.cls._check_policy_mark_but_no_tag_filter(policy) is False


class TestCheckPolicyMarkBadMessage(PolicyGenTester):

    def test_no_actions(self):
        policy = {'name': 'foo'}
        assert self.cls._check_policy_mark_for_op_bad_message(policy) is True

    def test_no_mark_actions_with_messages(self):
        policy = {
            'name': 'foo',
            'actions': [
                'stop',
                {'type': 'notify'},
                {'type': 'mark-for-op', 'op': 'stop'}
            ]
        }
        assert self.cls._check_policy_mark_for_op_bad_message(policy) is True

    def test_one_mark_action_ok(self):
        policy = {
            'name': 'foo',
            'actions': [
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-mytag',
                    'op': 'stop',
                    'message': 'foo-mark: {op}@{action_date}',
                    'days': 7
                }
            ]
        }
        assert self.cls._check_policy_mark_for_op_bad_message(policy) is True

    def test_two_mark_actions_ok(self):
        policy = {
            'name': 'foo',
            'actions': [
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-mytag',
                    'op': 'stop',
                    'message': 'foo-mark: {op}@{action_date}',
                    'days': 7
                },
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-myOTHERtag',
                    'op': 'terminate',
                    'message': 'foo-mark: {op}@{action_date}',
                    'days': 14
                }
            ]
        }
        assert self.cls._check_policy_mark_for_op_bad_message(policy) is True

    def test_one_mark_action_broken(self):
        policy = {
            'name': 'foo',
            'actions': [
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-mytag',
                    'op': 'stop',
                    'message': 'foo-mark {op}@{action_date}',
                    'days': 7
                }
            ]
        }
        assert self.cls._check_policy_mark_for_op_bad_message(policy) is False

    def test_two_mark_actions_broken(self):
        policy = {
            'name': 'foo',
            'actions': [
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-mytag',
                    'op': 'stop',
                    'message': 'foo-mark {op}@{action_date}',
                    'days': 7
                },
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-myOTHERtag',
                    'op': 'terminate',
                    'message': 'foo-mark {op}@{action_date}',
                    'days': 14
                }
            ]
        }
        assert self.cls._check_policy_mark_for_op_bad_message(policy) is False

    def test_one_of_many_actions_broken(self):
        policy = {
            'name': 'foo',
            'actions': [
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-mytag',
                    'op': 'stop',
                    'message': 'foo-mark: {op}@{action_date}',
                    'days': 7
                },
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-myOTHERtag',
                    'op': 'terminate',
                    'message': 'foo-mark {op}@{action_date}',
                    'days': 14
                },
                {
                    'type': 'mark-for-op',
                    'tag': 'c7n-myTHIRDtag',
                    'op': 'terminate',
                    'message': 'foo-mark: {op}@{action_date}',
                    'days': 28
                }
            ]
        }
        assert self.cls._check_policy_mark_for_op_bad_message(policy) is False


class TestGenerateCleanupPolicies(PolicyGenTester):

    def test_cleanup(self):
        lcleanup = {
            'name': 'c7n-cleanup-lambda',
            'comment': 'Find and alert on orphaned c7n Lambda functions',
            'resource': 'lambda',
            'actions': [{
                'type': 'notify',
                'violation_desc': 'The following cloud-custodian Lambda '
                                  'functions appear to be orphaned',
                'action_desc': 'and should probably be deleted',
                'subject': '[cloud-custodian {{ account }}] Orphaned '
                           'cloud-custodian Lambda funcs in {{ region }}',
                'to': ['me@example.com', 'foo']
            }],
            'filters': [
                {'tag:Project': 'cloud-custodian'},
                {'tag:Component': 'present'},
                {
                    'type': 'value',
                    'key': 'tag:Component',
                    'op': 'ne',
                    'value': 'c7n-cleanup-lambda'
                },
                {
                    'type': 'value',
                    'key': 'tag:Component',
                    'op': 'ne',
                    'value': 'c7n-cleanup-cwe'
                },
                {
                    'type': 'value',
                    'key': 'tag:Component',
                    'op': 'ne',
                    'value': 'foo'
                },
                {
                    'type': 'value',
                    'key': 'tag:Component',
                    'op': 'ne',
                    'value': 'bar'
                },
                {
                    'type': 'value',
                    'key': 'tag:Component',
                    'op': 'ne',
                    'value': 'baz'
                }
            ]
        }
        cwecleanup = {
            'name': 'c7n-cleanup-cwe',
            'comment': 'Find and alert on orphaned c7n CloudWatch Events',
            'resource': 'event-rule',
            'actions': [{
                'type': 'notify',
                'violation_desc': 'The following cloud-custodian CloudWatch '
                                  'Event rules appear to be orphaned',
                'action_desc': 'and should probably be deleted',
                'subject': '[cloud-custodian {{ account }}] Orphaned '
                           'cloud-custodian CW Event rules in {{ region }}',
                'to': ['me@example.com', 'foo']
            }],
            'filters': [
                {
                    'type': 'value',
                    'key': 'Name',
                    'op': 'glob',
                    'value': 'custodian-*'
                },
                {
                    'type': 'value',
                    'key': 'Name',
                    'op': 'ne',
                    'value': 'custodian-c7n-cleanup-lambda'
                },
                {
                    'type': 'value',
                    'key': 'Name',
                    'op': 'ne',
                    'value': 'custodian-c7n-cleanup-cwe'
                },
                {
                    'type': 'value',
                    'key': 'Name',
                    'op': 'ne',
                    'value': 'custodian-foo'
                },
                {
                    'type': 'value',
                    'key': 'Name',
                    'op': 'ne',
                    'value': 'custodian-bar'
                },
                {
                    'type': 'value',
                    'key': 'Name',
                    'op': 'ne',
                    'value': 'custodian-baz'
                }
            ]
        }
        policies = [
            {'mode': {'type': 'periodic'}, 'name': 'foo'},
            {'name': 'bar'},
            {'mode': {'type': 'periodic'}, 'name': 'baz'}
        ]
        assert self.cls._generate_cleanup_policies(policies) == [
            lcleanup, cwecleanup
        ]


class TestPolicyRst(PolicyGenTester):

    def test_rst_jenkins(self):
        policies = {
            'foo': 'bar',
            'baz': 'blam'
        }
        timestr = 'someTime'
        gitlink = 'https://example.com/org/repo/commit/abcd1234'
        expected = "this page built by `PE/custodian-config/foo 2 " \
            "<https://bento/job/2>`_ from `abcd1234 <%s>`_ at %s\n\n" % (
                gitlink, timestr
            )
        expected += "tableHere"
        with patch(
            'manheim_c7n_tools.policygen.PolicyGen._policy_rst_data',
            autospec=True
        ) as m_prd:
            m_prd.return_value = [
                ['aaa', '', 'comment-aaa'],
                ['zzz', 'region1', 'comment-zzz'],
                ['ddd', 'region2', 'comment-ddd']
            ]
            with patch.dict(os.environ, {
                'GIT_COMMIT': 'abcd1234',
                'BUILD_NUMBER': '2',
                'JOB_NAME': 'PE/custodian-config/foo',
                'BUILD_URL': 'https://bento/job/2'
            }, clear=True):
                with patch(
                    'manheim_c7n_tools.policygen.timestr', autospec=True
                ) as m_timestr:
                    with patch(
                        'manheim_c7n_tools.policygen.tabulate', autospec=True
                    ) as m_tabulate:
                        with patch(
                            'manheim_c7n_tools.policygen.git_html_url',
                            autospec=True
                        ) as ghu:
                            ghu.return_value = 'https://example.com/org/repo/'
                            m_tabulate.return_value = 'tableHere'
                            m_timestr.return_value = timestr
                            res = self.cls._policy_rst(policies)
        assert res == expected
        assert m_prd.mock_calls == [
            call(self.cls, {'foo': 'bar', 'baz': 'blam'})
        ]
        assert m_tabulate.mock_calls == [
            call(
                [
                    ['aaa', '', 'comment-aaa'],
                    ['ddd', 'region2', 'comment-ddd'],
                    ['zzz', 'region1', 'comment-zzz']
                ],
                headers=[
                    'Policy Name',
                    'Account(s) / Region(s)',
                    'Description/Comment'
                ],
                tablefmt='grid'
            )
        ]

    def test_rst_local(self):
        policies = {
            'foo': 'bar',
            'baz': 'blam'
        }
        timestr = 'someTime'
        gitlink = 'https://example.com/org/repo/commit/abcd1234'
        expected = "this page built locally from `abcd1234 <%s>`_ at %s" \
            "\n\n" % (gitlink, timestr)
        expected += "tableHere"
        with patch(
            'manheim_c7n_tools.policygen.PolicyGen._policy_rst_data',
            autospec=True
        ) as m_prd:
            m_prd.return_value = [
                ['aaa', '', 'comment-aaa'],
                ['zzz', 'region1', 'comment-zzz'],
                ['ddd', 'region2', 'comment-ddd']
            ]
            with patch.dict(os.environ, {
                'GIT_COMMIT': 'abcd1234'
            }, clear=True):
                with patch(
                    'manheim_c7n_tools.policygen.timestr', autospec=True
                ) as m_timestr:
                    with patch(
                        'manheim_c7n_tools.policygen.tabulate', autospec=True
                    ) as m_tabulate:
                        with patch(
                            'manheim_c7n_tools.policygen.git_html_url',
                            autospec=True
                        ) as ghu:
                            ghu.return_value = 'https://example.com/org/repo/'
                            m_tabulate.return_value = 'tableHere'
                            m_timestr.return_value = timestr
                            res = self.cls._policy_rst(policies)
        assert res == expected
        assert m_prd.mock_calls == [
            call(self.cls, {'foo': 'bar', 'baz': 'blam'})
        ]
        assert m_tabulate.mock_calls == [
            call(
                [
                    ['aaa', '', 'comment-aaa'],
                    ['ddd', 'region2', 'comment-ddd'],
                    ['zzz', 'region1', 'comment-zzz']
                ],
                headers=[
                    'Policy Name',
                    'Account(s) / Region(s)',
                    'Description/Comment'
                ],
                tablefmt='grid'
            )
        ]


class TestPolicyRstData(PolicyGenTester):

    def test_policy_rst_data(self):
        acct_policies = {
            'myAccount': {
                'region1': {
                    'fooA1': {'comment': 'bar-myAccount/region1'},
                    'baz': {'comment': 'blam'},
                    'myAccount/common': {'comment': 'c'},
                    'all_r1': {'comment': 'region1'},
                    'all_common': {'comment': 'region1'}
                },
                'region2': {
                    'fooA1': {'comment': 'bar-myAccount/region2'},
                    'baz': {'comment': 'blam'},
                    'myAccount/common': {'comment': 'c'},
                    'all_r2': {'comment': 'region2'},
                    'all_common': {'comment': 'region2'}
                },
                'region3': {
                    'foo': {'comment': 'bar-myAccount/region3'},
                    'myAccount/common': {'comment': 'c'},
                    'all_r3': {'comment': 'region3'},
                    'all_common': {'comment': 'region3'}
                }
            },
            'otherAccount': {
                'region1': {
                    'foo': {'comment': 'bar-otherAccount/region1'},
                    'otherAccount/common': {'comment': 'c'},
                    'all_r1': {'comment': 'region1'},
                    'all_common': {'comment': 'region1'}
                },
                'region2': {
                    'fooA2': {'comment': 'bar-otherAccount/region2'},
                    'baz': {'comment': 'blam'},
                    'otherAccount/common': {'comment': 'c'},
                    'all_r2': {'comment': 'region2'},
                    'all_common': {'comment': 'region2'}
                },
                'region3': {
                    'fooA2': {'comment': 'bar-otherAccount/region3'},
                    'baz': {'comment': 'blam'},
                    'otherAccount/common': {'comment': 'c'},
                    'all_r3': {'comment': 'region3'},
                    'all_common': {'comment': 'region3'}
                }
            }
        }
        assert self.cls._policy_rst_data(acct_policies) == [
            ['all_common', '', 'region3'],
            ['all_r1', 'myAccount (region1) otherAccount (region1)', 'region1'],
            ['all_r2', 'myAccount (region2) otherAccount (region2)', 'region2'],
            ['all_r3', 'myAccount (region3) otherAccount (region3)', 'region3'],
            [
                'baz',
                'myAccount (region1 region2) otherAccount (region2 region3)',
                'blam'
            ],
            [
                'foo',
                'myAccount (region3) otherAccount (region1)',
                'bar-otherAccount/region1'
            ],
            ['fooA1', 'myAccount (region1 region2)', 'bar-myAccount/region2'],
            [
                'fooA2',
                'otherAccount (region2 region3)',
                'bar-otherAccount/region3'
            ],
            ['myAccount/common', 'myAccount', 'c'],
            ['otherAccount/common', 'otherAccount', 'c']
        ]


class TestRegionsRst(PolicyGenTester):

    def test_regions(self):

        m_confA = Mock(spec_set=ManheimConfig)
        type(m_confA).regions = PropertyMock(
            return_value=['region1', 'region2', 'region3']
        )
        type(m_confA).account_name = PropertyMock(return_value='myAccount')
        type(m_confA).account_id = PropertyMock(return_value=1234567890)
        type(m_confA).config_path = PropertyMock(
            return_value='/tmp/conf.yml'
        )
        m_confB = Mock(spec_set=ManheimConfig)
        type(m_confB).regions = PropertyMock(
            return_value=['region2', 'region3']
        )
        type(m_confB).account_name = PropertyMock(return_value='otherAccount')
        type(m_confB).account_id = PropertyMock(return_value=987654321)
        type(m_confB).config_path = PropertyMock(
            return_value='/tmp/conf.yml'
        )

        def se_conf(_, aname):
            if aname == 'myAccount':
                return m_confA
            return m_confB

        self.m_conf.from_file.side_effect = se_conf
        res = self.cls._regions_rst()
        assert res == "  * myAccount (1234567890)\n\n" \
                      "    * region1\n    * region2\n    * region3\n\n" \
                      "  * otherAccount (987654321)\n\n" \
                      "    * region2\n    * region3\n\n"


class TestPolicyComment(PolicyGenTester):

    def test_comment(self):
        policy = {
            'comment': 'mycomment',
            'comments': 'mycomments',
            'description': 'mydescription'
        }
        assert self.cls._policy_comment(policy) == 'mycomment'

    def test_comments(self):
        policy = {
            'comments': 'mycomments',
            'description': 'mydescription'
        }
        assert self.cls._policy_comment(policy) == 'mycomments'

    def test_description(self):
        policy = {
            'description': 'mydescription'
        }
        assert self.cls._policy_comment(policy) == 'mydescription'

    def test_none(self):
        policy = {}
        assert self.cls._policy_comment(policy) == 'unknown'


class TestReadPolicies(PolicyGenTester):

    def test_read(self):

        def se_read(klass, fpath):
            name = fpath.split('/')[-1].split('.')[0]
            return {'file': fpath, 'name': name}

        with patch(
            'manheim_c7n_tools.policygen.os.listdir', autospec=True
        ) as mock_list:
            with patch(
                'manheim_c7n_tools.policygen.PolicyGen._read_file_yaml',
                autospec=True
            ) as mock_read:
                mock_list.return_value = [
                    'foo.yml',
                    'bar.yml',
                    'README.md'
                ]
                mock_read.side_effect = se_read
                res = self.cls._read_policies('rname')
        assert res == {
            'foo': {'file': 'policies/rname/foo.yml', 'name': 'foo'},
            'bar': {'file': 'policies/rname/bar.yml', 'name': 'bar'}
        }

    def test_read_bad_name(self):

        def se_read(klass, fpath):
            name = fpath.split('/')[-1].split('.')[0]
            if name == 'foo':
                name = 'wrongName'
            return {'file': fpath, 'name': name}

        with patch(
            'manheim_c7n_tools.policygen.os.listdir', autospec=True
        ) as mock_list:
            with patch(
                'manheim_c7n_tools.policygen.PolicyGen._read_file_yaml',
                autospec=True
            ) as mock_read:
                mock_list.return_value = [
                    'foo.yml',
                    'bar.yml',
                    'README.md'
                ]
                mock_read.side_effect = se_read
                with pytest.raises(RuntimeError) as ex:
                    self.cls._read_policies('rname')
        assert str(ex.value) == 'ERROR: Policy file foo.yml contains ' \
            'policy with name "wrongName".'

    def test_no_such_directory(self):

        def se_listdir(dirname):
            raise OSError(
                "[Errno 2] No such file or directory: '%s'" % dirname
            )

        with patch(
            'manheim_c7n_tools.policygen.os.listdir', autospec=True
        ) as mock_list:
            with patch(
                    'manheim_c7n_tools.policygen.PolicyGen._read_file_yaml',
                    autospec=True
            ) as mock_read:
                mock_list.side_effect = se_listdir
                res = self.cls._read_policies('foo')
        assert res == {}
        assert mock_list.mock_calls == [call('policies/foo')]
        assert mock_read.mock_calls == []


class TestReadFileYaml(PolicyGenTester):

    def test_read(self):
        m = mock_open(read_data="- foo\n- bar\n")
        with patch(
            'manheim_c7n_tools.policygen.open', m, create=True
        ) as m_open:
            res = self.cls._read_file_yaml('/foo/bar.yml')
        assert res == ['foo', 'bar']
        assert m_open.mock_calls == [
            call('/foo/bar.yml', 'r'),
            call().__enter__(),
            call().read(),
            call().__exit__(None, None, None)
        ]

    def test_read_exception(self):
        m = mock_open(read_data="  - foo:\n- bar")
        with patch(
            'manheim_c7n_tools.policygen.open', m, create=True
        ) as m_open:
            with pytest.raises(Exception):
                self.cls._read_file_yaml('/foo/bar.yml')
        assert m_open.mock_calls == [
            call('/foo/bar.yml', 'r'),
            call().__enter__(),
            call().read(),
            call().__exit__(None, None, None)
        ]


class TestTimestr(object):

    @freeze_time('2018-04-01 01:02:03', tz_offset=0)
    def test_timestr(self):
        assert policygen.timestr() == '2018-04-01 01:02:03 UTC'


class TestMain(object):

    def test_main(self):
        m_conf = Mock()
        with patch(
            'manheim_c7n_tools.policygen.PolicyGen', autospec=True
        ) as mock_pg:
            with patch('sys.argv', ['policygen', 'acctName']):
                with patch(
                    'manheim_c7n_tools.policygen.ManheimConfig', autospec=True
                ) as mock_cc:
                    mock_cc.from_file.return_value = m_conf
                    policygen.main()
        assert mock_cc.mock_calls == [
            call.from_file('manheim-c7n-tools.yml', 'acctName')
        ]
        assert mock_pg.mock_calls == [
            call(m_conf),
            call().run()
        ]

    def test_main_config_path(self):
        m_conf = Mock()
        with patch(
            'manheim_c7n_tools.policygen.PolicyGen', autospec=True
        ) as mock_pg:
            with patch('sys.argv', ['policygen', '-c', 'foo.yml', 'acctName']):
                with patch(
                    'manheim_c7n_tools.policygen.ManheimConfig', autospec=True
                ) as mock_cc:
                    mock_cc.from_file.return_value = m_conf
                    policygen.main()
        assert mock_cc.mock_calls == [
            call.from_file('foo.yml', 'acctName')
        ]
        assert mock_pg.mock_calls == [
            call(m_conf),
            call().run()
        ]
