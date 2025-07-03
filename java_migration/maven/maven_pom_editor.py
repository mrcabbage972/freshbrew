# type: ignore

import os
from typing import Any, Callable, Dict, List, Optional, Union

from lxml import etree


class MavenPomEditor:
    def __init__(self, pom_file: str) -> None:
        """
        Initialize the editor for a single pom.xml file.

        :param pom_file: Path to the pom.xml file.
        """
        self.pom_file: str = os.path.abspath(pom_file)
        self.tree = etree.parse(self.pom_file)
        self.root = self.tree.getroot()
        # Copy the namespace map and remap the default namespace (if present) to "m"
        self.namespaces: Dict[Optional[str], str] = self.root.nsmap.copy()
        if None in self.namespaces:
            self.namespaces["m"] = self.namespaces.pop(None)

    def ensure_element(
        self, parent: Union[str, etree._Element], tag: str, text: Optional[str] = None
    ) -> etree._Element:
        """
        Ensure that an element with the specified tag exists under the given parent.
        The parent can be an XPath string or an lxml Element.
        If it exists, return it; otherwise, create it and optionally set its text.

        :param parent: XPath of the parent element or the parent lxml Element.
        :param tag: Tag name with prefix for the desired child element (e.g., "m:executions").
        :param text: Optional text content to set for the element.
        :return: The existing or newly created element.
        """
        try:
            if isinstance(parent, str):
                parent_elements = self.root.xpath(parent, namespaces=self.namespaces)
                if not parent_elements:
                    raise ValueError(f"No parent element found for XPath '{parent}'.")
                parent_element = parent_elements[0]
            elif isinstance(parent, etree._Element):
                parent_element = parent
            else:
                raise TypeError("parent must be an XPath string or an lxml Element.")

            elements = parent_element.xpath(tag, namespaces=self.namespaces)
            if elements:
                if text is not None:
                    elements[0].text = text
                return elements[0]
            # If not found, add it using the create_sub_element method.
            new_element = self.create_sub_element(parent_element, tag)
            if text is not None:
                new_element.text = text
            return new_element
        except Exception as e:
            raise ValueError(f"Error ensuring element {tag} under {parent}: {e}")

    def create_sub_element(
        self, parent: etree._Element, tag: str, text: Optional[str] = None, attrib: Optional[Dict[str, str]] = None
    ) -> etree._Element:
        """
        Create a sub-element of the given parent element using a qualified tag name.
        This is similar to etree.SubElement but ensures the tag is properly qualified.

        :param parent: The parent element.
        :param tag: Tag name with prefix (e.g. "m:execution").
        :param text: Optional text content.
        :param attrib: Optional attributes.
        :return: The created sub-element.
        """
        sub_elem = etree.SubElement(parent, self._qname(tag), attrib=attrib if attrib else {})
        if text:
            sub_elem.text = text
        return sub_elem

    def _qname(self, tag: str) -> str:
        """
        Convert a tag with a prefix (e.g. "m:dependency") to a qualified name.
        If the tag is already qualified, return it unchanged.
        """
        if tag.startswith("{"):
            return tag
        if ":" in tag:
            prefix, local = tag.split(":", 1)
            ns = self.namespaces.get(prefix)
            if ns is None:
                raise ValueError(f"No namespace found for prefix '{prefix}'")
            return f"{{{ns}}}{local}"
        return tag

    def _save(self) -> None:
        """Save the modified XML tree back to the pom.xml file."""
        self.tree.write(self.pom_file, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    def update_element_text(self, xpath: str, new_text: str) -> None:
        """
        Update the text content of element(s) matching the XPath.

        :param xpath: XPath expression (e.g. ".//m:version").
        :param new_text: New text content.
        :raises ValueError: If no elements match.
        """
        elements = self.root.xpath(xpath, namespaces=self.namespaces)
        if not elements:
            raise ValueError(f"XPath '{xpath}' did not match any elements in {self.pom_file}.")
        for elem in elements:
            elem.text = new_text
        self._save()

    def element_exists(self, xpath: str) -> bool:
        """
        Check if element(s) matching the XPath exist.

        :param xpath: XPath expression.
        :return: True if found, else False.
        """
        elements = self.root.xpath(xpath, namespaces=self.namespaces)
        return bool(elements)

    def add_element(
        self, parent_xpath: str, tag: str, text: str | None = None, attrib: dict[str, str] | None = None
    ) -> etree._Element:
        """
        Add a new element under the first element matching the parent XPath.

        :param parent_xpath: XPath to locate the parent element.
        :param tag: The tag name of the new element (use a prefix, e.g. "m:dependency").
        :param text: Optional text content.
        :param attrib: Optional attributes.
        :return: The newly created element.
        :raises ValueError: If no parent element is found.
        """
        parents = self.root.xpath(parent_xpath, namespaces=self.namespaces)
        if not parents:
            raise ValueError(f"No parent element found for XPath '{parent_xpath}' in {self.pom_file}.")
        parent = parents[0]
        new_elem = etree.Element(self._qname(tag), attrib=attrib if attrib else {})
        if text:
            new_elem.text = text
        parent.append(new_elem)
        self._save()
        return new_elem

    #
    # Plugin helper functions
    #
    def get_plugin(self, group_id: str, artifact_id: str) -> Optional[etree._Element]:
        """
        Retrieve a plugin element by its groupId and artifactId.

        :param group_id: Plugin's groupId.
        :param artifact_id: Plugin's artifactId.
        :return: Plugin element if found; else None.
        """
        plugins = self.root.xpath(".//m:plugin", namespaces=self.namespaces)
        for plugin in plugins:
            gid = plugin.find(self._qname("m:groupId"))
            aid = plugin.find(self._qname("m:artifactId"))
            if (
                gid is not None
                and aid is not None
                and gid.text
                and aid.text
                and gid.text.strip() == group_id
                and aid.text.strip() == artifact_id
            ):
                return plugin
        return None

    def plugin_exists(self, group_id: str, artifact_id: str) -> bool:
        """
        Check if the specified plugin exists.

        :param group_id: Plugin's groupId.
        :param artifact_id: Plugin's artifactId.
        :return: True if found; else False.
        """
        return self.get_plugin(group_id, artifact_id) is not None

    def update_plugin(self, group_id: str, artifact_id: str, update_func: Callable[[etree._Element], None]) -> bool:
        """
        Update a plugin using the provided update function.
        The update function is given the plugin element to modify.

        :param group_id: Plugin's groupId.
        :param artifact_id: Plugin's artifactId.
        :param update_func: A function that takes the plugin element.
        :return: True if the plugin was found and updated; else False.
        """
        plugin = self.get_plugin(group_id, artifact_id)
        if plugin is None:
            return False
        update_func(plugin)
        self._save()
        return True

    def add_plugin(
        self,
        group_id: str,
        artifact_id: str,
        version: Optional[str] = None,
        configuration: Optional[Dict[str, str]] = None,
        executions: Optional[List[Dict[str, Any]]] = None,
    ) -> etree._Element:
        """
        Add a new plugin under the <build>/<plugins> section.

        :param group_id: Plugin's groupId.
        :param artifact_id: Plugin's artifactId.
        :param version: Optional version.
        :param configuration: Optional configuration as a dict (tag: text).
        :param executions: Optional list of executions (each as a dict of execution details).
        :return: The newly created plugin element.
        """
        # Ensure the parent elements exist.
        if not self.element_exists("m:build"):
            self.add_element(".", "m:build")
        if not self.element_exists("m:build/m:plugins"):
            self.add_element("m:build", "m:plugins")
        new_plugin = self.add_element("m:build/m:plugins", "m:plugin")
        self.add_element("m:build/m:plugins/m:plugin[last()]", "m:groupId", text=group_id)
        self.add_element("m:build/m:plugins/m:plugin[last()]", "m:artifactId", text=artifact_id)
        if version is not None:
            self.add_element("m:build/m:plugins/m:plugin[last()]", "m:version", text=version)
        if configuration:
            self.add_element("m:build/m:plugins/m:plugin[last()]", "m:configuration")
            for tag, value in configuration.items():
                self.add_element("m:build/m:plugins/m:plugin[last()]/m:configuration", f"m:{tag}", text=value)
        if executions:
            self.add_element("m:build/m:plugins/m:plugin[last()]", "m:executions")
            for exec_dict in executions:
                self.add_element("m:build/m:plugins/m:plugin[last()]/m:executions", "m:execution")
                for key, value in exec_dict.items():
                    if isinstance(value, list):
                        self.add_element(
                            "m:build/m:plugins/m:plugin[last()]/m:executions/m:execution[last()]", f"m:{key}"
                        )
                        for item in value:
                            # Simple heuristic: remove trailing "s" to form a singular tag name.
                            self.add_element(
                                "m:build/m:plugins/m:plugin[last()]/m:executions/m:execution[last()]/m:" + key,
                                f"m:{key[:-1]}",
                                text=str(item),
                            )
                    else:
                        self.add_element(
                            "m:build/m:plugins/m:plugin[last()]/m:executions/m:execution[last()]",
                            f"m:{key}",
                            text=str(value),
                        )
        return new_plugin

    #
    # Dependency helper functions
    #
    def get_dependency(self, group_id: str, artifact_id: str) -> Optional[etree._Element]:
        """
        Retrieve a dependency element by its groupId and artifactId.

        :param group_id: Dependency's groupId.
        :param artifact_id: Dependency's artifactId.
        :return: Dependency element if found; else None.
        """
        deps = self.root.xpath(".//m:dependency", namespaces=self.namespaces)
        for dep in deps:
            gid = dep.find(self._qname("m:groupId"))
            aid = dep.find(self._qname("m:artifactId"))
            if (
                gid is not None
                and aid is not None
                and gid.text
                and aid.text
                and gid.text.strip() == group_id
                and aid.text.strip() == artifact_id
            ):
                return dep
        return None

    def dependency_exists(self, group_id: str, artifact_id: str) -> bool:
        """
        Check if the specified dependency exists.

        :param group_id: Dependency's groupId.
        :param artifact_id: Dependency's artifactId.
        :return: True if found; else False.
        """
        return self.get_dependency(group_id, artifact_id) is not None

    def update_dependency(self, group_id: str, artifact_id: str, update_func: Callable[[etree._Element], None]) -> bool:
        """
        Update an existing dependency using the provided update function.

        :param group_id: Dependency's groupId.
        :param artifact_id: Dependency's artifactId.
        :param update_func: A function that takes the dependency element.
        :return: True if updated; else False.
        """
        dep = self.get_dependency(group_id, artifact_id)
        if dep is None:
            return False
        update_func(dep)
        self._save()
        return True

    def add_dependency(
        self, group_id: str, artifact_id: str, version: str, scope: Optional[str] = None
    ) -> etree._Element:
        """
        Add a new dependency under the <dependencies> section.

        :param group_id: Dependency's groupId.
        :param artifact_id: Dependency's artifactId.
        :param version: Dependency version.
        :param scope: Optional dependency scope (e.g. "test").
        :return: The newly created dependency element.
        """
        if not self.element_exists("m:dependencies"):
            self.add_element(".", "m:dependencies")
        dep = self.get_dependency(group_id, artifact_id)
        if dep is not None:
            self.ensure_element(dep, "m:groupId", text=group_id)
            self.ensure_element(dep, "m:artifactId", text=artifact_id)
            self.ensure_element(dep, "m:version", text=version)
        else:
            new_dep = self.add_element("m:dependencies", "m:dependency")
            self.add_element("m:dependencies/m:dependency[last()]", "m:groupId", text=group_id)
            self.add_element("m:dependencies/m:dependency[last()]", "m:artifactId", text=artifact_id)
            self.add_element("m:dependencies/m:dependency[last()]", "m:version", text=version)
            if scope:
                self.add_element("m:dependencies/m:dependency[last()]", "m:scope", text=scope)
            return new_dep

    def ensure_managed_dependency(
        self, group_id: str, artifact_id: str, version: str, scope: Optional[str] = None
    ) -> etree._Element:
        """
        Ensure a dependency exists in the <dependencyManagement><dependencies> section.
        Adds or updates the dependency. Uses ensure_element logic.

        :param group_id: Dependency groupId.
        :param artifact_id: Dependency artifactId.
        :param version: Dependency version (can be a property like ${junit.version}).
        :param scope: Optional dependency scope.
        :return: The managed dependency element.
        """

        # Ensure <dependencyManagement> and <dependencies> exist
        mgmt_elem = self.ensure_element(".", "m:dependencyManagement")
        deps_elem = self.ensure_element(mgmt_elem, "m:dependencies")

        # Check if dependency already exists in management
        existing_dep = None
        found_deps = deps_elem.xpath(
            f"m:dependency[m:groupId='{group_id}' and m:artifactId='{artifact_id}']", namespaces=self.namespaces
        )
        if found_deps:
            existing_dep = found_deps[0]

        if existing_dep is not None:
            # Update existing managed dependency
            self.ensure_element(existing_dep, "m:version", text=version)
            if scope:
                self.ensure_element(existing_dep, "m:scope", text=scope)
            else:
                # Remove scope if it exists and is not needed
                scope_elem = existing_dep.find("m:scope", namespaces=self.namespaces)
                if scope_elem is not None:
                    existing_dep.remove(scope_elem)
            dep_element = existing_dep
        else:
            # Add new managed dependency
            dep_element = self.create_sub_element(deps_elem, "m:dependency")
            self.create_sub_element(dep_element, "m:groupId", text=group_id)
            self.create_sub_element(dep_element, "m:artifactId", text=artifact_id)
            self.create_sub_element(dep_element, "m:version", text=version)
            if scope:
                self.create_sub_element(dep_element, "m:scope", text=scope)

        self._save()  # Save after ensuring the dependency
        return dep_element

    def ensure_property(self, property_name: str, property_value: str) -> etree._Element:
        """
        Ensure a property exists in the <properties> section. Adds or updates.

        :param property_name: The name of the property (e.g., "junit.version").
        :param property_value: The value of the property.
        :return: The property element.
        """
        properties_elem = self.ensure_element(".", "m:properties")
        # Use ensure_element which handles creation or update of text content
        prop_elem = self.ensure_element(properties_elem, f"m:{property_name}", text=property_value)
        self._save()  # Save after ensuring the property
        return prop_elem

    def add_skip_plugin_config(self, parent_plugin_element: etree._Element):
        """Adds <configuration><skip>true</skip></configuration> to a plugin element."""
        config_elem = self.ensure_element(parent_plugin_element, "m:configuration")
        self.ensure_element(config_elem, "m:skip", text="true")
        self._save()  # Save after adding config
