"""
Copyright (c) 2021, VRAI Labs and/or its affiliates. All rights reserved.

This software is licensed under the Apache License, Version 2.0 (the
"License") as published by the Apache Software Foundation.

You may not use this file except in compliance with the License. You may
obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
"""
from __future__ import annotations

import asyncio

from . import session_functions
from .cookie_and_header import get_id_refresh_token_from_cookie, get_access_token_from_cookie, get_anti_csrf_header, \
    get_rid_header, get_refresh_token_from_cookie
from .exceptions import raise_unauthorised_exception, raise_try_refresh_token_exception
from .interfaces import RecipeInterface
from typing import TYPE_CHECKING

from supertokens_python.async_to_sync_wrapper import check_event_loop
from supertokens_python.normalised_url_path import NormalisedURLPath
from supertokens_python.process_state import ProcessState, AllowedProcessStates

if TYPE_CHECKING:
    from typing import Union, List
    from .utils import SessionConfig
    from supertokens_python.querier import Querier
from .session_class import Session


class HandshakeInfo:

    def __init__(self, info):
        self.access_token_blacklisting_enabled = info['accessTokenBlacklistingEnabled']
        self.jwt_signing_public_key = info['jwtSigningPublicKey']
        self.jwt_signing_public_key_expiry_time = info['jwtSigningPublicKeyExpiryTime']
        self.anti_csrf = info['antiCsrf']
        self.access_token_validity = info['accessTokenValidity']
        self.refresh_token_validity = info['refreshTokenValidity']

    def update_jwt_signing_public_key_info(self, new_key, new_expiry):
        self.jwt_signing_public_key = new_key
        self.jwt_signing_public_key_expiry_time = new_expiry


class RecipeImplementation(RecipeInterface):
    def __init__(self, querier: Querier, config: SessionConfig):
        super().__init__()
        self.querier = querier
        self.config = config
        self.handshake_info: Union[HandshakeInfo, None] = None

        async def call_get_handshake_info():
            try:
                await self.get_handshake_info()
            except Exception:
                pass

        if config.framework.lower() == 'flask' or config.framework.lower() == 'django':
            check_event_loop()
            loop = asyncio.get_event_loop()
            loop.run_until_complete(call_get_handshake_info())
        else:
            asyncio.create_task(call_get_handshake_info())

    async def get_handshake_info(self) -> HandshakeInfo:
        if self.handshake_info is None:
            ProcessState.get_instance().add_state(AllowedProcessStates.CALLING_SERVICE_IN_GET_HANDSHAKE_INFO)
            response = await self.querier.send_post_request(NormalisedURLPath('/recipe/handshake'), {})
            self.handshake_info = HandshakeInfo({
                **response,
                'antiCsrf': self.config.anti_csrf
            })
        return self.handshake_info

    def update_jwt_signing_public_key_info(self, new_key, new_expiry):
        if self.handshake_info is not None:
            self.handshake_info.update_jwt_signing_public_key_info(new_key, new_expiry)

    async def create_new_session(self, request: any, user_id: str, jwt_payload: Union[dict, None] = None,
                                 session_data: Union[dict, None] = None) -> Session:
        session = await session_functions.create_new_session(self, user_id, jwt_payload, session_data)
        access_token = session['accessToken']
        refresh_token = session['refreshToken']
        id_refresh_token = session['idRefreshToken']
        new_session = Session(self, access_token['token'], session['session']['handle'],
                              session['session']['userId'], session['session']['userDataInJWT'])
        new_session.new_access_token_info = access_token
        new_session.new_refresh_token_info = refresh_token
        new_session.new_id_refresh_token_info = id_refresh_token
        if 'antiCsrfToken' in session and session['antiCsrfToken'] is not None:
            new_session.new_anti_csrf_token = session['antiCsrfToken']
        request.set_session(new_session)
        return request.get_session()

    async def get_session(self, request: any, anti_csrf_check: Union[bool, None] = None,
                          session_required: bool = True) -> Union[Session, None]:
        id_refresh_token = get_id_refresh_token_from_cookie(request)
        if id_refresh_token is None:
            if not session_required:
                return None
            raise_unauthorised_exception('Session does not exist. Are you sending the session tokens in the '
                                         'request as cookies?', False)
        access_token = get_access_token_from_cookie(request)
        if access_token is None:
            raise_try_refresh_token_exception('Access token has expired. Please call the refresh API')
        anti_csrf_token = get_anti_csrf_header(request)
        if anti_csrf_check is None:
            anti_csrf_check = request.method().lower() != 'get'
        new_session = await session_functions.get_session(self, access_token, anti_csrf_token, anti_csrf_check,
                                                          get_rid_header(request) is not None)
        if 'accessToken' in new_session:
            access_token = new_session['accessToken']['token']

        session = Session(self, access_token, new_session['session']['handle'],
                          new_session['session']['userId'], new_session['session']['userDataInJWT'])

        if 'accessToken' in new_session:
            session.new_access_token_info = new_session['accessToken']
        request.set_session(session)
        return request.get_session()

    async def refresh_session(self, request: any) -> Session:
        id_refresh_token = get_id_refresh_token_from_cookie(request)
        if id_refresh_token is None:
            raise_unauthorised_exception('Session does not exist. Are you sending the session tokens in the request '
                                         'as cookies?', False)
        refresh_token = get_refresh_token_from_cookie(request)
        if refresh_token is None:
            raise_unauthorised_exception('Refresh token not found. Are you sending the refresh token in the '
                                         'request as a cookie?')
        anti_csrf_token = get_anti_csrf_header(request)
        new_session = await session_functions.refresh_session(self, refresh_token, anti_csrf_token,
                                                              get_rid_header(request) is not None)
        access_token = new_session['accessToken']
        refresh_token = new_session['refreshToken']
        id_refresh_token = new_session['idRefreshToken']
        session = Session(self, access_token['token'], new_session['session']['handle'],
                          new_session['session']['userId'], new_session['session']['userDataInJWT'])
        session.new_access_token_info = access_token
        session.new_refresh_token_info = refresh_token
        session.new_id_refresh_token_info = id_refresh_token
        if 'antiCsrfToken' in new_session and new_session['antiCsrfToken'] is not None:
            session.new_anti_csrf_token = new_session['antiCsrfToken']
        request.set_session(session)

        return request.get_session()

    async def revoke_session(self, session_handle: str) -> bool:
        return await session_functions.revoke_session(self, session_handle)

    async def revoke_all_sessions_for_user(self, user_id: str) -> List[str]:
        return await session_functions.revoke_all_sessions_for_user(self, user_id)

    async def get_all_session_handles_for_user(self, user_id: str) -> List[str]:
        return await session_functions.get_all_session_handles_for_user(self, user_id)

    async def revoke_multiple_sessions(self, session_handles: List[str]) -> List[str]:
        return await session_functions.revoke_multiple_sessions(self, session_handles)

    async def get_session_information(self, session_handle: str) -> dict:
        return await session_functions.get_session_information(self, session_handle)

    async def update_session_data(self, session_handle: str, new_session_data: dict) -> None:
        await session_functions.update_session_data(self, session_handle, new_session_data)

    async def update_jwt_payload(self, session_handle: str, new_jwt_payload: dict) -> None:
        await session_functions.update_jwt_payload(self, session_handle, new_jwt_payload)

    async def get_access_token_lifetime_ms(self) -> int:
        return (await self.get_handshake_info()).access_token_validity

    async def get_refresh_token_lifetime_ms(self) -> int:
        return (await self.get_handshake_info()).refresh_token_validity
