from abc import ABC

import pytest

from core.backend.internal_data_processing_base import InternalDataProcessingBase


class MinimalImplementation(InternalDataProcessingBase):
    """Minimal implementation of InternalDataProcessingBase for testing"""

    def __init__(self):
        self._sessions_data = {}
        self._feedbacks_data = {}
        self._concatenate_data = {}
        self._prompts_data = {}
        self._costs_data = {}
        self._abort_data = {}
        self._processing_data = {}
        self._vectors_data = {}
        self._subprompts_data = {}
        self._custom_actions_data = {}
        self._chainofthoughts_data = {}
        self._initialized = False

    async def initialize(self) -> None:
        self._initialized = True

    @property
    def plugin_name(self) -> str:
        return "minimal_implementation"

    @property
    def sessions(self):
        return self._sessions_data

    @property
    def feedbacks(self):
        return self._feedbacks_data

    @property
    def concatenate(self):
        return self._concatenate_data

    @property
    def prompts(self):
        return self._prompts_data

    @property
    def costs(self):
        return self._costs_data

    @property
    def abort(self):
        return self._abort_data

    @property
    def processing(self):
        return self._processing_data

    @property
    def vectors(self):
        return self._vectors_data

    @property
    def subprompts(self):
        return self._subprompts_data

    @property
    def custom_actions(self):
        return self._custom_actions_data

    @property
    def chainofthoughts(self):
        return self._chainofthoughts_data

    async def append_data(self, container_name: str, data_identifier: str, data: str) -> None:
        pass

    async def remove_data(self, container_name: str, datafile_name: str, data: str) -> None:
        pass

    async def read_data_content(self, data_container, data_file):
        pass

    async def write_data_content(self, data_container, data_file, data):
        pass

    async def update_pricing(self, container_name, datafile_name, pricing_data):
        pass

    async def update_prompt_system_message(self, channel_id, thread_id, message):
        pass

    async def update_session(self, data_container, data_file, role, content):
        pass

    async def remove_data_content(self, data_container, data_file):
        pass

    async def list_container_files(self, container_name):
        pass

    async def create_container(self, data_container: str) -> None:
        pass

    def create_container_sync(self, data_container: str) -> None:
        pass

    async def file_exists(self, container_name: str, file_name: str) -> bool:
        return False

    async def clear_container(self, container_name: str) -> None:
        pass

    def clear_container_sync(self, container_name: str) -> None:
        pass


class TestInternalDataProcessingBase:

    def test_cannot_instantiate_abstract_class(self):
        """Test that we cannot instantiate the abstract class directly"""
        with pytest.raises(TypeError):
            InternalDataProcessingBase()

    def test_must_implement_all_abstract_methods(self):
        """Test that all abstract methods must be implemented"""
        class IncompleteImplementation(InternalDataProcessingBase):
            pass

        with pytest.raises(TypeError):
            IncompleteImplementation()

    def test_can_instantiate_complete_implementation(self):
        """Test that we can instantiate a complete implementation"""
        impl = MinimalImplementation()
        assert isinstance(impl, InternalDataProcessingBase)
        assert isinstance(impl, ABC)

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test that initialization works"""
        impl = MinimalImplementation()
        assert not impl._initialized
        await impl.initialize()
        assert impl._initialized

    def test_plugin_name(self):
        """Test that plugin_name is accessible"""
        impl = MinimalImplementation()
        assert impl.plugin_name == "minimal_implementation"

    def test_all_properties_exist(self):
        """Test that all required properties exist and are accessible"""
        impl = MinimalImplementation()

        # Test all properties
        assert hasattr(impl, 'sessions')
        assert hasattr(impl, 'feedbacks')
        assert hasattr(impl, 'concatenate')
        assert hasattr(impl, 'prompts')
        assert hasattr(impl, 'costs')
        assert hasattr(impl, 'abort')
        assert hasattr(impl, 'processing')
        assert hasattr(impl, 'vectors')
        assert hasattr(impl, 'subprompts')
        assert hasattr(impl, 'custom_actions')
        assert hasattr(impl, 'chainofthoughts')

    @pytest.mark.asyncio
    async def test_async_methods_exist(self):
        """Test that all async methods exist and are callable"""
        impl = MinimalImplementation()

        # Test all async methods
        await impl.append_data("test", "test", "test")
        await impl.remove_data("test", "test", "test")
        await impl.read_data_content("test", "test")
        await impl.write_data_content("test", "test", "test")
        await impl.update_pricing("test", "test", {})
        await impl.update_prompt_system_message("test", "test", "test")
        await impl.update_session("test", "test", "test", "test")
        await impl.remove_data_content("test", "test")
        await impl.list_container_files("test")
        await impl.create_container("test")
        await impl.file_exists("test", "test")
        await impl.clear_container("test")

    def test_sync_methods_exist(self):
        """Test that all sync methods exist and are callable"""
        impl = MinimalImplementation()

        impl.create_container_sync("test")
        impl.clear_container_sync("test")

    def test_inheritance(self):
        """Test proper inheritance from InternalDataPluginBase"""
        impl = MinimalImplementation()
        assert isinstance(impl, InternalDataProcessingBase)

class TestInternalDataProcessingBaseSignatures:
    """Tests to verify method signatures match the abstract base class"""

    @pytest.mark.asyncio
    async def test_append_data_signature(self):
        impl = MinimalImplementation()
        from inspect import signature
        sig = signature(impl.append_data)
        assert str(sig) == "(container_name: str, data_identifier: str, data: str) -> None"

    @pytest.mark.asyncio
    async def test_remove_data_signature(self):
        impl = MinimalImplementation()
        from inspect import signature
        sig = signature(impl.remove_data)
        assert str(sig) == "(container_name: str, datafile_name: str, data: str) -> None"

    def test_property_types(self):
        impl = MinimalImplementation()
        assert isinstance(impl.sessions, dict)
        assert isinstance(impl.feedbacks, dict)
        assert isinstance(impl.concatenate, dict)
        assert isinstance(impl.prompts, dict)
        assert isinstance(impl.costs, dict)
        assert isinstance(impl.abort, dict)
        assert isinstance(impl.processing, dict)
        assert isinstance(impl.vectors, dict)
        assert isinstance(impl.subprompts, dict)
        assert isinstance(impl.custom_actions, dict)
        assert isinstance(impl.chainofthoughts, dict)
