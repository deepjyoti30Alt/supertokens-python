# Copyright (c) 2021, VRAI Labs and/or its affiliates. All rights reserved.
#
# This software is licensed under the Apache License, Version 2.0 (the
# "License") as published by the Apache Software Foundation.
#
# You may not use this file except in compliance with the License. You may
# obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar, Union

_T = TypeVar('_T')


class EmailDeliveryInterface(ABC, Generic[_T]):
    @abstractmethod
    def send_email(self, email_input: Union[_T, None]) -> Any:
        pass


class TypeInput(ABC, Generic[_T]):
    service: EmailDeliveryInterface[_T]

    def override(self, original_impl: EmailDeliveryInterface[_T]) -> EmailDeliveryInterface[_T]:
        return original_impl

    def __init__(self, service: EmailDeliveryInterface[_T]) -> None:
        self.service = service
