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

from typing import Any, Dict

from supertokens_python.ingredients.emaildelivery.services.smtp import (
    GetContentResult, ServiceInterface)
from supertokens_python.recipe.emailverification.types import \
    TypeEmailVerificationEmailDeliveryInput
from supertokens_python.recipe.thirdpartypasswordless.types import \
    TypeThirdPartyPasswordlessEmailDeliveryInput


class ServiceImplementation(ServiceInterface[TypeEmailVerificationEmailDeliveryInput]):
    def __init__(self, tppless_service_implementation: ServiceInterface[TypeThirdPartyPasswordlessEmailDeliveryInput]) -> None:
        super().__init__(tppless_service_implementation.transporter)
        self.tppless_service_implementation = tppless_service_implementation

    async def send_raw_email(self, input_: GetContentResult, user_context: Dict[str, Any]) -> None:
        return await self.tppless_service_implementation.send_raw_email(input_, user_context)

    async def get_content(self, input_: TypeEmailVerificationEmailDeliveryInput) -> GetContentResult:
        return await self.tppless_service_implementation.get_content(input_)
