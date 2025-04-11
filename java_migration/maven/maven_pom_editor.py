import os
from typing import Any, Callable, Dict, List, Optional

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

    def ensure_element(self, parent_xpath: str, tag: str) -> etree._Element:
        """
        Ensure that an element with the specified tag exists under the first element matching parent_xpath.
        If it exists, return it; otherwise, create it and then return it.

        :param parent_xpath: XPath of the parent element.
        :param tag: Tag name (with prefix) for the desired child element.
        :return: The existing or newly created element.
        """
        # Build a full XPath query for the child under the parent.
        full_xpath = f"{parent_xpath}/{tag}"
        elements = self.root.xpath(full_xpath, namespaces=self.namespaces)
        if elements:
            return elements[0]
        # If not found, add it using the add_element method.
        return self.add_element(parent_xpath, tag)

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

        :param tag: Tag in "prefix:local" format.
        :return: A qualified tag "{namespace}local".
        :raises ValueError: if the prefix is not found in the namespace map.
        """
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
        new_dep = self.add_element("m:dependencies", "m:dependency")
        self.add_element("m:dependencies/m:dependency[last()]", "m:groupId", text=group_id)
        self.add_element("m:dependencies/m:dependency[last()]", "m:artifactId", text=artifact_id)
        self.add_element("m:dependencies/m:dependency[last()]", "m:version", text=version)
        if scope:
            self.add_element("m:dependencies/m:dependency[last()]", "m:scope", text=scope)
        return new_dep
