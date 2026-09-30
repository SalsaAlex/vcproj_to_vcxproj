import xml
import xml.etree
import xml.etree.ElementTree as ET

import locale

import argparse
import os

def makeelementwtext(elname, text):
    elret = ET.Element(elname)
    elret.text = text
    return elret

def configtype_map(map):
    result = ""
    if map == "1":
        result = "Application"
    elif map == "2":
        result = "DynamicLibrary"
    elif map == "4":
        result = "StaticLibrary"
    return result

#returns .vcxproj and .vcxproj.filters
def to_vcxproj(vcproj_xmlfilepath : str):
    wheretosavevcxproj = vcproj_xmlfilepath[:str(vcproj_xmlfilepath).rfind(".")] + ".vcxproj"
    wheretosavevcxprojfilters = vcproj_xmlfilepath[:str(vcproj_xmlfilepath).rfind(".")] + ".vcxproj.filters"
    
    with open(vcproj_xmlfilepath) as f:
        vcproj_xmlfile = f.read()
    
    vcproj_xmltree = ET.fromstring(vcproj_xmlfile)
    
    vcxproj_entry = ET.Element("Project", {   "DefaultTargets": "Build", "xmlns":"http://schemas.microsoft.com/developer/msbuild/2003"   } )
    vcxproj_projconfigs = ET.Element("ItemGroup", {"Label":"ProjectConfigurations"})
    vcxproj_globals = ET.Element("PropertyGroup", {"Label":"Globals"})
    vcxproj_compileitems = ET.Element("ItemGroup")
    vcxproj_includeitems = ET.Element("ItemGroup")
    
    vcxproj_filters = ET.Element("Project", { "ToolsVersion": "4.0", "xmlns":"http://schemas.microsoft.com/developer/msbuild/2003"  })
    vcxproj_declarefilters = ET.Element("ItemGroup")
    vcxproj_declaresources = ET.Element("ItemGroup")
    vcxproj_declareheaders = ET.Element("ItemGroup")
    
    configs = [] #name, type, platform
    configurations = vcproj_xmltree.find("Configurations")
    for configuration in configurations.iter("Configuration"):
        name = configuration.attrib["Name"]
        type = name[:name.rfind("|")]
        platform = name[name.find("|")+1:]
        configtype = configuration.attrib["ConfigurationType"]
        outdir = configuration.attrib["OutputDirectory"]
        intdir = configuration.attrib["IntermediateDirectory"]
        warninglevel = 0
        subsystem = ""
        gendebuginfo = 0
        additlibdirs = ""
        additlibs = ""
        defines = ""
        includes = ""
    
        for toolconfig in configuration.iter("Tool"):
            if toolconfig.attrib["Name"] == "VCCLCompilerTool":
                warninglevel = locale.atoi(toolconfig.attrib["WarningLevel"])       if "WarningLevel" in toolconfig.attrib else 0
                defines = toolconfig.attrib["PreprocessorDefinitions"]              if "PreprocessorDefinitions" in toolconfig.attrib else ""
                includes = toolconfig.attrib["AdditionalIncludeDirectories"]        if "AdditionalIncludeDirectories" in toolconfig.attrib else ""
            if toolconfig.attrib["Name"] == "VCLinkerTool":
                if "SubSystem" in toolconfig.attrib:
                    subsystem = "Windows" if toolconfig.attrib["SubSystem"]==2 else "Console"
                additlibdirs = toolconfig.attrib["AdditionalLibraryDirectories"]    if "AdditionalLibraryDirectories" in toolconfig.attrib else ""
                additlibs = toolconfig.attrib["AdditionalDependencies"]             if "AdditionalDependencies" in toolconfig.attrib else ""
                if "GenerateDebugInformation" in toolconfig.attrib:
                    gendebuginfo = 1 if toolconfig.attrib["GenerateDebugInformation"]=="true" else 0
    
        #fixup additional dependencies
        additlibs = additlibs.replace(" ", ";")
    
        configs.append({"gendebuginfo":gendebuginfo, 
                        "additlibdirs":additlibdirs, 
                        "additlibs":additlibs, 
                        "subsystem":subsystem, 
                        
                        "warninglevel":warninglevel,
                        "defines":defines,
                        "includes":includes,
                        
                        "outdir":outdir,
                        "intdir":intdir,
                        
                        "name":name, 
                        "type":type, 
                        "platform":platform,
                        "configtype":configtype
                        })
    
    
    vcxproj_entry.append(vcxproj_projconfigs)
    vcxproj_entry.append(vcxproj_globals)
    vcxproj_entry.append(ET.Element("Import", {"Project":"$(VCTargetsPath)\\Microsoft.Cpp.Default.props"}))
    for entry in configs:
        propertygroupconfig = ET.Element("PropertyGroup", 
                                         {"Condition":f"'$(Configuration)|$(Platform)'=='{entry["name"]}'",
                                          "Label":"Configuration"})
        propertygroupconfig.append(makeelementwtext("ConfigurationType", configtype_map(entry["configtype"])))
        propertygroupconfig.append(makeelementwtext("UseDebugLibraries", "true" if entry["type"]=="Debug" else "false"))
        propertygroupconfig.append(makeelementwtext("PlatformToolset", "v143"))
        propertygroupconfig.append(makeelementwtext("CharacterSet", "NotSet"))
        vcxproj_entry.append(propertygroupconfig)
        
    vcxproj_entry.append(ET.Element("Import", {"Project":"$(VCTargetsPath)\\Microsoft.Cpp.props"}))
    vcxproj_entry.append(ET.Element("ImportGroup", {"Label":"ExtensionSettings"}))
    vcxproj_entry.append(ET.Element("ImportGroup", {"Label":"Shared"}))
    for entry in configs:
        propertysheets = ET.Element("ImportGroup", 
                                         {"Label":"PropertySheets",
                                          "Condition":f"'$(Configuration)|$(Platform)'=='{entry["name"]}'"})
        propertysheets.append(ET.Element("Import", 
                                         {"Project":"$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props",
                                          "Condition":"exists('$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props')",
                                          "Label":"LocalAppDataPlatform"}))
        vcxproj_entry.append(propertysheets)
    vcxproj_entry.append(ET.Element("PropertyGroup", {"Label":"UserMacros"}))
    propertygroupdirsettings = ET.Element("PropertyGroup", 
                                 {"Condition":f"'$(Configuration)|$(Platform)'=='{configs[0]["name"]}'"})
    propertygroupdirsettings.append(makeelementwtext("OutDir", configs[0]["outdir"]))
    propertygroupdirsettings.append(makeelementwtext("IntDir", configs[0]["intdir"]))
    vcxproj_entry.append(propertygroupdirsettings)
    
    for entry in configs:
        itemdefgroup = ET.Element("ItemDefinitionGroup", 
                                         {"Condition":f"'$(Configuration)|$(Platform)'=='{entry["name"]}'"})
        clcompile = ET.Element("ClCompile")
        link = ET.Element("Link")
        itemdefgroup.append(clcompile)
        itemdefgroup.append(link)
        vcxproj_entry.append(itemdefgroup)
    
        clcompile.append(makeelementwtext("WarningLevel", f"Level{entry["warninglevel"]}"))
        clcompile.append(makeelementwtext("SDLCheck", "false"))
        clcompile.append(makeelementwtext("PreprocessorDefinitions", entry["defines"]))
        clcompile.append(makeelementwtext("AdditionalIncludeDirectories", entry["includes"]))
        clcompile.append(makeelementwtext("LanguageStandard", "stdcpp17"))
        clcompile.append(makeelementwtext("MultiProcessorCompilation", "true"))
        clcompile.append(makeelementwtext("FunctionLevelLinking", "false"))
    
        link.append(makeelementwtext("SubSystem", entry["subsystem"]))
        link.append(makeelementwtext("GenerateDebugInformation", "true" if entry["gendebuginfo"]==1 else "false"))
        link.append(makeelementwtext("AdditionalLibraryDirectories", entry["additlibdirs"]))
        link.append(makeelementwtext("AdditionalDependencies", entry["additlibs"]))
    
    
    vcxproj_entry.append(vcxproj_compileitems)
    vcxproj_entry.append(vcxproj_includeitems)
    
    vcxproj_entry.append(ET.Element("Import", {"Project":"$(VCTargetsPath)\Microsoft.Cpp.targets"}))
    vcxproj_entry.append(ET.Element("ImportGroup", {"Label":"ExtensionTargets"}))
    
    vcxproj_filters.append(vcxproj_declarefilters)
    vcxproj_filters.append(vcxproj_declaresources)
    vcxproj_filters.append(vcxproj_declareheaders)
    
    ###
    #end
    ###
    
    vcxproj_globals.append(makeelementwtext("VCProjectVersion", "17.0"))
    
    for entry in configs:
        projconfig = ET.Element("ProjectConfiguration", {"Include": entry["name"]})
        projconfig.append(makeelementwtext("Configuration", entry["type"]))
        projconfig.append(makeelementwtext("Platform", entry["platform"]))
    
        vcxproj_projconfigs.append(projconfig)
    
    files = vcproj_xmltree.find("Files")
    if files.find("Filter") != None:
        for filters in list(files.iter("Filter")):
            filtername = filters.attrib["Name"]
            vcxproj_declarefilters.append(ET.Element("Filter", {"Include":filtername}))
            for file in filters.iter("File"):
                path = file.attrib["RelativePath"]
                if path.endswith(".h") or path.endswith(".hpp"):
                    vcxproj_includeitems.append(ET.Element("ClInclude", {"Include": path}))
                    headerfilefilter = ET.Element("ClInclude", {"Include": path})
                    headerfilefilter.append(makeelementwtext("Filter", filtername))
                    vcxproj_declareheaders.append(headerfilefilter)
                else:
                    vcxproj_compileitems.append(ET.Element("ClCompile", {"Include": path}))
                    sourcefilefilter = ET.Element("ClCompile", {"Include": path})
                    sourcefilefilter.append(makeelementwtext("Filter", filtername))
                    vcxproj_declaresources.append(sourcefilefilter)
    else:
        for file in list(files.iter("File")):
            path = file.attrib["RelativePath"]
            if path.endswith(".h") or path.endswith(".hpp"):
                vcxproj_includeitems.append(ET.Element("ClInclude", {"Include": path}))
            else:
                vcxproj_compileitems.append(ET.Element("ClCompile", {"Include": path}))
    
    ET.indent(vcxproj_entry)
    ET.indent(vcxproj_filters)
    
    
    #main proj
    vcxprojbuffer = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
    vcxprojbuffer += ET.tostring(vcxproj_entry).decode()
    
    #filters
    vcxprojfilterbuffer = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
    vcxprojfilterbuffer += ET.tostring(vcxproj_filters).decode()

    return vcxprojbuffer, vcxprojfilterbuffer