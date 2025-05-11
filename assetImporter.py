import unreal
from pathlib import Path

def importAssets(filePath):

    filename = []
    # Fetch all the files
    paths = Path(filePath)
    for file in paths.iterdir():
        filename.append(file.as_posix())

    # getting asset tools
    assetTools = unreal.AssetToolsHelpers.get_asset_tools()

    #creating ImportData
    assetImportData = unreal.AutomatedAssetImportData()
    assetImportData.destination_path = '/Game/AutoImports'
    assetImportData.filenames = filename
    assetImportData.replace_existing = True

    #Importing assets
    assetTools.import_assets_automated(assetImportData)

    #Filter Asset Type
    filterasset('/Game/AutoImports')


def filterasset(folderpath):

    mesh = []
    texture = []

    #Loading assets
    assetLib = unreal.EditorAssetLibrary()
    for assetPath in assetLib.list_assets(folderpath):
        #removing reduntant name from unreal assetname
        assetPath = assetPath.split('.')[0]
        asset = assetLib.load_asset(assetPath)

        #Create Seperate list
        if isinstance(asset, unreal.StaticMesh):
            mesh.append(asset)
        elif isinstance(asset, unreal.Texture):
            texture.append(asset)

    if mesh:
        processStaticMesh(mesh)

    if texture:
        processTextures(texture)

def processStaticMesh(meshes):

    SMlib = unreal.StaticMeshEditorSubsystem()

    for mesh in meshes:
        # Disable Nanite Support
        meshNaniteSettings = mesh.get_editor_property('nanite_settings')
        if meshNaniteSettings.enabled:
            meshNaniteSettings.enabled = False
            SMlib.set_nanite_settings(mesh, meshNaniteSettings, apply_changes=True)

        #Set Enable Generate lightmap UVs
        meshBuildSettings = SMlib.get_lod_build_settings(mesh,0)
        if not meshBuildSettings.generate_lightmap_u_vs:
            meshBuildSettings.generate_lightmap_u_vs = True

        # Set Min Lightmap resoultion to 256
        if meshBuildSettings.min_lightmap_resolution != 256:
            meshBuildSettings.min_lightmap_resolution = 256
        SMlib.set_lod_build_settings(mesh,0, meshBuildSettings)

        #Set Asset Category from Name
        meshName = mesh.get_name()
        if "_arch" in meshName.lower():
            SMlib.set_lod_group(mesh,"LevelArchitecture")
        elif any(s in meshName.lower() for s in ("_large", "_big")):
            SMlib.set_lod_group(mesh, "LargeProp")
        elif any(s in meshName.lower() for s in ("_small","_prop")):
            SMlib.set_lod_group(mesh, "SmallProp")
        elif "_foliage" in meshName.lower():
            SMlib.set_lod_group(mesh, "Foliage")
        
        #Disable auto compute LOD Distance
        if mesh.is_lod_screen_size_auto_computed():

            # Accessing MeshReductionOptions
            autoLod = unreal.StaticMeshReductionOptions()
            autoLod.set_editor_property("auto_compute_lod_screen_size",False)
            
            # Additional meshSettings are required to update lods
            reductionOption = unreal.StaticMeshReductionSettings()
            reductionOption.set_editor_property('percent_triangles',1.0)

            reductionArray = unreal.Array(unreal.StaticMeshReductionSettings)
            reductionArray.append(reductionOption)

            autoLod.set_editor_property('reduction_settings', reductionArray)

            # Disabling Option
            SMlib.set_lods(mesh,autoLod)

        # Disable Ray Tracing
        MAS = unreal.MeshApproximationSettings()
        if MAS.support_ray_tracing:
            mesh.set_editor_property('support_ray_tracing', False)

        # Setting Collision Presets;
        # Getting Default body Instance
        body = mesh.get_editor_property('body_setup')
        instance = body.get_editor_property('default_instance')

        # Object Type = World Dynamic
        instance.set_editor_property('collision_profile_name', "BlockAllDynamic")
        instance.set_editor_property('object_type', unreal.CollisionChannel.ECC_WORLD_DYNAMIC)

        # Collision Enabled = Query and Physics
        instance.set_editor_property('collision_enabled', unreal.CollisionEnabled.QUERY_AND_PHYSICS)


def processTextures(textures):

    for texture in textures:

        # Lossy Compression Amount = OddleRD0 20(Medium)
        compAmount = texture.get_editor_property('lossy_compression_amount')
        desiredAmount = unreal.TextureLossyCompressionAmount.TLCA_MEDIUM
        if compAmount !=  desiredAmount:
            texture.set_editor_property('lossy_compression_amount', desiredAmount)

        # ASTC Compression Quality = ASTC8x8 block
        compQuality = texture.get_editor_property('compression_quality')
        desiredQuality = unreal.TextureCompressionQuality.TCQ_MEDIUM
        if compQuality != desiredQuality :
            texture.set_editor_property('compression_quality', desiredQuality)


        # Catergorizing different texture types
        texName = texture.get_name()
        # Diffuse
        if any(s in texName.lower() for s in ('_diffuse', '_d', '_albedo', '_basecolor')):

            diffMip = unreal.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE
            diffComp = unreal.TextureCompressionSettings.TC_DEFAULT
            diffGroup = unreal.TextureGroup.TEXTUREGROUP_WORLD

            setTextureProperty(texture,diffMip,diffComp,diffGroup)
        # Normal
        elif any(s in texName.lower() for s in ('_normal','_n')):

            normalMip = unreal.TextureMipGenSettings.TMGS_SHARPEN0
            normalComp = unreal.TextureCompressionSettings.TC_NORMALMAP
            normalGroup = unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP

            setTextureProperty(texture, normalMip, normalComp, normalGroup)
        # Specular
        elif '_orm' in texName.lower():

            ormMip = unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS
            ormComp = unreal.TextureCompressionSettings.TC_MASKS
            ormGroup = unreal.TextureGroup.TEXTUREGROUP_WORLD_SPECULAR

            setTextureProperty(texture, ormMip, ormComp, ormGroup)


def setTextureProperty(tex,desiredGen,desiredSetting,desiredGroup):
    # Getting current property values
    mipGen = tex.get_editor_property('mip_gen_settings')
    compSetting = tex.get_editor_property('compression_settings')
    texGroup = tex.get_editor_property('lod_group')
    
    # Mip Gen Settings 
    if mipGen != desiredGen:
        tex.set_editor_property('mip_gen_settings', desiredGen)

    # Compression Setting = Based on texture type
    if compSetting != desiredSetting:
        tex.set_editor_property('compression_settings', desiredSetting)
    
        # Texture Group (Additional Filter for character files based on Directory)
    if "/character/" in tex.get_path_name().lower():
        if desiredGroup.get_display_name() == 'WorldNormalMap':
            desiredGroup = unreal.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP
        elif desiredGroup.get_display_name() == 'WorldSpecular':
            desiredGroup =unreal.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR
        else:
            desiredGroup = unreal.TextureGroup.TEXTUREGROUP_CHARACTER

        if texGroup != desiredGroup:
            tex.set_editor_property('lod_group', desiredGroup)
    else:
        if texGroup != desiredGroup:
            tex.set_editor_property('lod_group', desiredGroup)