<script setup>
import { ref, onMounted, computed, nextTick } from "vue";
import { api } from "./api";
import { printLabel } from "./printerManager";
import { Html5Qrcode } from "html5-qrcode";
import {
  Package,
  Plus,
  Search,
  MapPin,
  Printer,
  ExternalLink,
  Camera,
  Loader2,
  X,
  PlusCircle,
  Pencil,
  Trash2,
  QrCode,
  Settings,
  ScanLine,
  Minus,
  Home,
  Grid,
  Box,
  Inbox,
  ChevronRight,
  ChevronDown,
  FolderPlus,
  Sun,
  Moon,
  Laptop,
  Download
} from "lucide-vue-next";

const items = ref([]);
const locations = ref([]);
const searchQuery = ref("");
const loading = ref(true);
const selectedLocationId = ref(null);
const isSidebarOpenMobile = ref(false);

const currentTheme = ref("system");

const installPromptEvent = ref(null);

const showItemModal = ref(false);
const showLocationModal = ref(false);
const showSettingsModal = ref(false);
const showQrScannerModal = ref(false);
const showDetailsModal = ref(false);
const showBoxContentsModal = ref(false);

const aiLoading = ref(false);
const editingItemId = ref(null);
const editingLocationId = ref(null);
const selectedItem = ref(null);
const selectedLocation = ref(null);
const boxContainedItems = ref([]);

let html5QrScanner = null;

const systemSettings = ref({
  print_enabled: true
});

const settingsForm = ref({
  gemini_api_key: "",
  gemini_model: "gemini-3.5-flash-lite",
  print_enabled: true,
  printer_transport: "ble",
  printer_language: "fichero",
  label_width: 40,
  label_height: 15,
  printer_ip: "",
  printer_ble_name_prefix: "FICHERO,D11"
});
const availableModels = ref([]);
const settingsSaving = ref(false);

const locationForm = ref({
  name: "",
  location_type: "box",
  parent_id: null,
  description: "",
});

const itemForm = ref({
  name: "",
  description: "",
  location_id: null,
  quantity: 1,
  is_consumable: false,
  source_url: "",
  metadata_fields: {},
});

const customMetaKey = ref("");
const customMetaValue = ref("");

const applyTheme = (theme) => {
  currentTheme.value = theme;
  localStorage.setItem("homestack_theme", theme);

  const isDark =
    theme === "dark" ||
    (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);

  if (isDark) {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
};

const initTheme = () => {
  const saved = localStorage.getItem("homestack_theme") || "system";
  applyTheme(saved);

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (currentTheme.value === "system") {
      applyTheme("system");
    }
  });
};

const installPwa = async () => {
  if (!installPromptEvent.value) return;
  installPromptEvent.value.prompt();
  const { outcome } = await installPromptEvent.value.userChoice;
  if (outcome === "accepted") {
    installPromptEvent.value = null;
    showSettingsModal.value = false;
  }
};

const getLocationIcon = (type) => {
  switch (type) {
    case 'room': return Home;
    case 'shelf': return Grid;
    case 'drawer': return Inbox;
    default: return Box;
  }
};

const getLocationTypeBadgeClass = (type) => {
  switch (type) {
    case 'room': return 'bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-800';
    case 'shelf': return 'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800';
    case 'drawer': return 'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800';
    default: return 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800';
  }
};

const flattenedLocationTree = computed(() => {
  const result = [];
  const traverse = (parentId = null, depth = 0) => {
    const directChildren = locations.value.filter((l) => l.parent_id === parentId);
    for (const loc of directChildren) {
      result.push({ ...loc, depth });
      traverse(loc.id, depth + 1);
    }
  };
  traverse(null, 0);
  return result;
});

const getLocationBreadcrumbs = (locId) => {
  if (!locId) return [];
  const crumbs = [];
  let current = locations.value.find((l) => l.id === locId);
  while (current) {
    crumbs.unshift(current);
    current = current.parent_id ? locations.value.find((l) => l.id === current.parent_id) : null;
  }
  return crumbs;
};

const activeContainer = computed(() => {
  if (!selectedLocationId.value) return null;
  return locations.value.find((l) => l.id === selectedLocationId.value) || null;
});

const loadData = async () => {
  loading.value = true;
  try {
    const [itemsRes, locationsRes] = await Promise.all([
      api.getItems(),
      api.getLocations(),
    ]);
    items.value = itemsRes.data;
    locations.value = locationsRes.data;
  } catch (err) {
    console.error("Failed to load inventory data:", err);
  } finally {
    loading.value = false;
  }
};

const displayedItems = computed(() => {
  if (!selectedLocationId.value) return items.value;

  const collectChildIds = (parentId) => {
    const directChildren = locations.value.filter((l) => l.parent_id === parentId);
    let ids = [parentId];
    for (const child of directChildren) {
      ids = ids.concat(collectChildIds(child.id));
    }
    return ids;
  };

  const validLocationIds = collectChildIds(selectedLocationId.value);
  return items.value.filter((i) => validLocationIds.includes(i.location_id));
});

const handleSearch = async () => {
  if (!searchQuery.value.trim()) return loadData();
  loading.value = true;
  try {
    const res = await api.searchItems(searchQuery.value);
    items.value = res.data;
  } catch (err) {
    console.error("Search failed:", err);
  } finally {
    loading.value = false;
  }
};

const startQrScanner = async () => {
  showQrScannerModal.value = true;
  await nextTick();

  try {
    html5QrScanner = new Html5Qrcode("qr-camera-viewport");
    await html5QrScanner.start(
      { facingMode: "environment" },
      { fps: 10, qrbox: { width: 220, height: 220 } },
      onScanSuccess,
      () => {}
    );
  } catch (err) {
    alert("Unable to access camera: " + err.message);
    stopQrScanner();
  }
};

const stopQrScanner = async () => {
  if (html5QrScanner) {
    try {
      if (html5QrScanner.isScanning) {
        await html5QrScanner.stop();
      }
      html5QrScanner.clear();
    } catch (e) {
      console.warn("Scanner stop warning:", e);
    }
    html5QrScanner = null;
  }
  showQrScannerModal.value = false;
};

const onScanSuccess = async (decodedText) => {
  await stopQrScanner();
  try {
    const res = await api.scanLookup(decodedText.trim());
    if (res.data.entity_type === "item") {
      selectedItem.value = res.data.data;
      showDetailsModal.value = true;
    } else if (res.data.entity_type === "location") {
      selectedLocation.value = res.data.data;
      boxContainedItems.value = res.data.contained_items;
      showBoxContentsModal.value = true;
    }
  } catch (err) {
    alert(`No item or container found matching: "${decodedText}"`);
  }
};

const printItemLabel = async (itemId) => {
  await printLabel(() => api.getItemPrintPayload(itemId));
};

const printLocationLabel = async (locationId) => {
  await printLabel(() => api.getLocationPrintPayload(locationId));
};

const adjustQuantity = async (delta) => {
  if (!selectedItem.value) return;
  const newQty = Math.max(0, (selectedItem.value.quantity || 0) + delta);
  try {
    const res = await api.updateItem(selectedItem.value.id, { quantity: newQty });
    selectedItem.value.quantity = res.data.quantity;
    await loadData();
  } catch (err) {
    alert("Failed to update quantity: " + err.message);
  }
};

const loadSettings = async () => {
  try {
    const res = await api.getSettings();
    systemSettings.value = res.data;
  } catch (err) {
    console.error("Failed to load global settings", err);
  }
};

const openSettingsModal = async () => {
  try {
    const res = await api.getSettings();
    const d = res.data;
    
    settingsForm.value = {
      gemini_api_key: d.gemini_api_key || "",
      gemini_model: d.gemini_model || "gemini-3.5-flash-lite",
      print_enabled: d.print_enabled ?? true,
      printer_transport: d.printer_transport || "ble",
      printer_language: d.printer_language || "fichero",
      label_width: d.label_width || 40,
      label_height: d.label_height || 15,
      printer_ip: d.printer_ip || "",
      printer_ble_name_prefix: d.printer_ble_name_prefix || "FICHERO,D11"
    };
    availableModels.value = d.available_models || [];
    showSettingsModal.value = true;
  } catch (err) {
    alert("Failed to load settings: " + err.message);
  }
};

const saveSettings = async () => {
  settingsSaving.value = true;
  try {
    await api.updateSettings(settingsForm.value);
    showSettingsModal.value = false;
    await loadSettings(); 
    alert("Settings saved successfully!");
  } catch (err) {
    alert("Failed to save settings: " + err.message);
  } finally {
    settingsSaving.value = false;
  }
};

const openCreateItemModal = (targetLocationId = null) => {
  editingItemId.value = null;
  resetItemForm();
  itemForm.value.location_id = targetLocationId || selectedLocationId.value || null;
  showItemModal.value = true;
};

const openEditItemModal = (item) => {
  editingItemId.value = item.id;
  itemForm.value = {
    name: item.name,
    description: item.description || "",
    location_id: item.location_id,
    quantity: item.quantity,
    is_consumable: item.is_consumable,
    source_url: item.source_url || "",
    metadata_fields: item.metadata_fields ? { ...item.metadata_fields } : {},
  };
  showDetailsModal.value = false;
  showBoxContentsModal.value = false;
  showItemModal.value = true;
};

const handleDeleteItem = async (itemId) => {
  if (!confirm("Are you sure you want to delete this item?")) return;
  try {
    await api.deleteItem(itemId);
    showDetailsModal.value = false;
    await loadData();
  } catch (err) {
    alert("Failed to delete item: " + err.message);
  }
};

const openCreateLocationModal = (suggestedParentId = null, defaultType = "box") => {
  editingLocationId.value = null;
  locationForm.value = {
    name: "",
    location_type: defaultType,
    parent_id: suggestedParentId !== null ? suggestedParentId : selectedLocationId.value,
    description: "",
  };
  showLocationModal.value = true;
};

const openEditLocationModal = (loc) => {
  editingLocationId.value = loc.id;
  locationForm.value = {
    name: loc.name,
    location_type: loc.location_type || "box",
    parent_id: loc.parent_id,
    description: loc.description || "",
  };
  showLocationModal.value = true;
};

const handleDeleteLocation = async (locationId) => {
  if (!confirm("Delete this container? Contained items will become unassigned.")) return;
  try {
    await api.deleteLocation(locationId);
    if (selectedLocationId.value === locationId) {
      selectedLocationId.value = null;
    }
    await loadData();
  } catch (err) {
    alert("Failed to delete location: " + err.message);
  }
};

const submitLocation = async () => {
  if (!locationForm.value.name.trim()) {
    alert("Location name is required!");
    return;
  }
  try {
    if (editingLocationId.value) {
      await api.updateLocation(editingLocationId.value, locationForm.value);
    } else {
      await api.createLocation(locationForm.value);
    }
    showLocationModal.value = false;
    await loadData();
  } catch (err) {
    alert("Failed to save location: " + err.message);
  }
};

const handleImageUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  aiLoading.value = true;
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await api.analyzeImage(formData);
    const aiData = res.data;

    itemForm.value.name = aiData.name || "";
    itemForm.value.description = aiData.description || "";
    itemForm.value.quantity = aiData.quantity || 1;
    itemForm.value.is_consumable = aiData.is_consumable || false;
    itemForm.value.metadata_fields = aiData.metadata_fields || {};
  } catch (err) {
    alert("AI Analysis failed: " + (err.response?.data?.detail || err.message));
  } finally {
    aiLoading.value = false;
  }
};

const addCustomMetadata = () => {
  if (!customMetaKey.value.trim()) return;
  itemForm.value.metadata_fields[customMetaKey.value.trim()] = customMetaValue.value.trim();
  customMetaKey.value = "";
  customMetaValue.value = "";
};

const removeMetadataField = (key) => {
  delete itemForm.value.metadata_fields[key];
};

const submitItem = async (andPrint = false) => {
  if (!itemForm.value.name.trim()) {
    alert("Item name is required!");
    return;
  }

  try {
    let savedItemId = editingItemId.value;
    if (editingItemId.value) {
      await api.updateItem(editingItemId.value, itemForm.value);
    } else {
      const res = await api.createItem(itemForm.value);
      savedItemId = res.data.id;
    }

    showItemModal.value = false;
    resetItemForm();
    await loadData();

    if (andPrint && savedItemId) {
      await printItemLabel(savedItemId);
    }
  } catch (err) {
    alert("Failed to save item: " + err.message);
  }
};

const resetItemForm = () => {
  itemForm.value = {
    name: "",
    description: "",
    location_id: null,
    quantity: 1,
    is_consumable: false,
    source_url: "",
    metadata_fields: {},
  };
  editingItemId.value = null;
};

onMounted(() => {
  initTheme();
  loadSettings();
  loadData();

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    installPromptEvent.value = e;
  });
});
</script>

<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex flex-col font-sans overflow-x-hidden transition-colors duration-200">
    <header class="bg-indigo-600 dark:bg-indigo-950 text-white shadow-sm sticky top-0 z-20 transition-colors">
      <div class="max-w-7xl mx-auto px-3 sm:px-4 h-16 flex items-center justify-between gap-2 sm:gap-4">
        <div class="flex items-center gap-1.5 sm:gap-2 shrink-0">
          <Package class="w-5 h-5 sm:w-6 sm:h-6 text-indigo-200" />
          <h1 class="text-sm sm:text-lg font-bold tracking-tight">
            HomeStack<span class="hidden sm:inline"> Inventory</span>
          </h1>
        </div>

        <div class="flex-1 max-w-md relative flex items-center min-w-0">
          <input
            v-model="searchQuery"
            @keyup.enter="handleSearch"
            type="text"
            placeholder="Search items, specs, QR..."
            class="w-full bg-indigo-700/60 dark:bg-indigo-900/60 text-white placeholder-indigo-300 text-xs sm:text-sm rounded-lg pl-8 pr-8 py-1.5 sm:py-2 border border-indigo-500 dark:border-indigo-800 focus:outline-none focus:ring-2 focus:ring-white truncate"
          />
          <Search class="w-3.5 h-3.5 text-indigo-300 absolute left-2.5" />
          <button
            @click="startQrScanner"
            class="absolute right-1.5 p-1 text-indigo-200 hover:text-white transition cursor-pointer"
            title="Scan QR Code (Camera)"
          >
            <ScanLine class="w-4 h-4" />
          </button>
        </div>

        <div class="flex items-center gap-1.5 sm:gap-2 shrink-0">
          <button
            @click="openSettingsModal"
            class="p-1.5 sm:p-2 bg-indigo-700/60 dark:bg-indigo-900/60 hover:bg-indigo-700 dark:hover:bg-indigo-800 rounded-lg text-white transition cursor-pointer"
            title="Configuration & Theme"
          >
            <Settings class="w-4 h-4 sm:w-5 sm:h-5 text-indigo-100" />
          </button>

          <button
            @click="openCreateItemModal()"
            class="flex items-center gap-1 sm:gap-1.5 bg-indigo-500 dark:bg-indigo-600 hover:bg-indigo-400 dark:hover:bg-indigo-500 text-xs sm:text-sm px-2.5 sm:px-3 py-1.5 sm:py-2 rounded-lg font-medium transition cursor-pointer"
          >
            <Plus class="w-4 h-4" />
            <span class="hidden sm:inline">Add Item</span>
          </button>
        </div>
      </div>
    </header>

    <main class="flex-grow max-w-7xl mx-auto px-3 sm:px-4 py-4 sm:py-6 w-full grid grid-cols-1 md:grid-cols-4 gap-4 sm:gap-6">
      
      <aside class="md:col-span-1 space-y-4">
        <div class="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800 p-3 sm:p-4 transition-colors">
          <div class="flex items-center justify-between mb-2">
            <div
              @click="isSidebarOpenMobile = !isSidebarOpenMobile"
              class="flex items-center gap-1.5 cursor-pointer md:cursor-default"
            >
              <MapPin class="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
              <h2 class="font-semibold text-gray-800 dark:text-gray-200 text-xs sm:text-sm">
                Storage
              </h2>
              <ChevronDown
                class="w-3.5 h-3.5 text-gray-400 md:hidden transition-transform duration-200"
                :class="{ 'rotate-180': isSidebarOpenMobile }"
              />
            </div>

            <button
              @click.stop="openCreateLocationModal(null, 'room')"
              class="text-[11px] bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 font-semibold px-2 py-0.5 rounded-md flex items-center gap-1 cursor-pointer transition shrink-0"
              title="Add a new root room"
            >
              <PlusCircle class="w-3 h-3" /> Room
            </button>
          </div>

          <div :class="isSidebarOpenMobile ? 'block' : 'hidden md:block'">
            <div
              @click="selectedLocationId = null"
              class="flex items-center justify-between text-xs py-2 px-2.5 rounded-lg cursor-pointer transition mb-2"
              :class="selectedLocationId === null ? 'bg-indigo-50 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 font-bold' : 'hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-700 dark:text-gray-300'"
            >
              <div class="flex items-center gap-2">
                <Package class="w-3.5 h-3.5 text-gray-400" />
                <span>All Storage (Global)</span>
              </div>
              <span class="text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded-full font-medium">{{ items.length }}</span>
            </div>

            <div v-if="locations.length === 0" class="text-xs text-gray-400 py-3 text-center">
              No storage locations yet.<br/>Click "+ Room" to create one.
            </div>

            <div v-else class="space-y-1 max-h-[300px] md:max-h-[600px] overflow-y-auto pr-1">
              <div
                v-for="loc in flattenedLocationTree"
                :key="loc.id"
                @click="selectedLocationId = loc.id"
                class="group flex items-center justify-between text-xs py-1.5 rounded-lg cursor-pointer transition border border-transparent"
                :class="selectedLocationId === loc.id ? 'bg-indigo-50 dark:bg-indigo-950/80 text-indigo-900 dark:text-indigo-200 border-indigo-100 dark:border-indigo-900 font-semibold' : 'hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-700 dark:text-gray-300'"
                :style="{ paddingLeft: `${Math.min(loc.depth * 10 + 6, 36)}px`, paddingRight: '6px' }"
              >
                <div class="flex items-center gap-1.5 truncate">
                  <component :is="getLocationIcon(loc.location_type)" class="w-3.5 h-3.5 shrink-0" :class="selectedLocationId === loc.id ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-400'" />
                  <span class="truncate">{{ loc.name }}</span>
                </div>

                <div class="flex items-center gap-0.5 shrink-0">
                  <button
                    v-if="systemSettings.print_enabled"
                    @click.stop="printLocationLabel(loc.id)"
                    class="p-1 hover:text-indigo-600 dark:hover:text-indigo-400 text-gray-400 rounded cursor-pointer"
                    title="Print container label"
                  >
                    <Printer class="w-3 h-3" />
                  </button>
                  <button
                    @click.stop="openCreateLocationModal(loc.id, loc.location_type === 'room' ? 'shelf' : 'box')"
                    class="p-1 hover:text-emerald-600 dark:hover:text-emerald-400 text-gray-400 rounded cursor-pointer"
                    title="Add container inside this"
                  >
                    <FolderPlus class="w-3 h-3" />
                  </button>
                  <button
                    @click.stop="openEditLocationModal(loc)"
                    class="p-1 hover:text-blue-600 dark:hover:text-blue-400 text-gray-400 rounded cursor-pointer"
                    title="Edit container"
                  >
                    <Pencil class="w-3 h-3" />
                  </button>
                  <button
                    @click.stop="handleDeleteLocation(loc.id)"
                    class="p-1 hover:text-red-600 dark:hover:text-red-400 text-gray-400 rounded cursor-pointer"
                    title="Delete container"
                  >
                    <Trash2 class="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <section class="md:col-span-3 space-y-4">

        <div v-if="activeContainer" class="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800 p-3 sm:p-4 transition-colors">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div class="flex items-start gap-2.5 sm:gap-3">
              <div class="p-2 sm:p-3 rounded-xl border shrink-0" :class="getLocationTypeBadgeClass(activeContainer.location_type)">
                <component :is="getLocationIcon(activeContainer.location_type)" class="w-5 h-5 sm:w-6 sm:h-6" />
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-1.5 mb-0.5">
                  <span class="text-[9px] sm:text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border" :class="getLocationTypeBadgeClass(activeContainer.location_type)">
                    {{ activeContainer.location_type }}
                  </span>
                  <span class="text-[11px] font-mono text-gray-400 font-semibold">{{ activeContainer.qr_code }}</span>
                </div>
                <h2 class="text-base sm:text-lg font-bold text-gray-900 dark:text-gray-100 leading-tight truncate">{{ activeContainer.name }}</h2>
                <p class="text-xs text-indigo-600 dark:text-indigo-400 font-medium flex items-center gap-1 mt-0.5 truncate">
                  <span v-for="(crumb, idx) in getLocationBreadcrumbs(activeContainer.id)" :key="crumb.id" class="flex items-center gap-1 truncate">
                    <span @click="selectedLocationId = crumb.id" class="cursor-pointer hover:underline truncate">{{ crumb.name }}</span>
                    <ChevronRight v-if="idx < getLocationBreadcrumbs(activeContainer.id).length - 1" class="w-3 h-3 text-gray-400 shrink-0" />
                  </span>
                </p>
              </div>
            </div>

            <div class="grid grid-cols-2 sm:flex sm:flex-wrap items-center gap-2 shrink-0 pt-1 sm:pt-0 border-t sm:border-t-0 border-gray-50 dark:border-gray-800">
              <button
                v-if="systemSettings.print_enabled"
                @click="printLocationLabel(activeContainer.id)"
                class="col-span-2 sm:col-span-1 px-3 py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg flex items-center justify-center gap-1.5 shadow-xs cursor-pointer transition"
              >
                <Printer class="w-3.5 h-3.5" />
                <span>Print Box Label</span>
              </button>

              <button
                @click="openCreateLocationModal(activeContainer.id, activeContainer.location_type === 'room' ? 'shelf' : 'box')"
                class="px-2.5 py-1.5 text-xs font-semibold bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg flex items-center justify-center gap-1 cursor-pointer transition truncate"
              >
                <FolderPlus class="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                <span>+ Sub-Box</span>
              </button>

              <button
                @click="openCreateItemModal(activeContainer.id)"
                class="px-2.5 py-1.5 text-xs font-semibold bg-gray-900 dark:bg-gray-100 hover:bg-black dark:hover:bg-white text-white dark:text-gray-900 rounded-lg flex items-center justify-center gap-1 cursor-pointer transition truncate"
              >
                <Plus class="w-3.5 h-3.5" />
                <span>Store Item</span>
              </button>
            </div>
          </div>
        </div>

        <div class="flex items-center justify-between">
          <h3 class="text-xs sm:text-sm font-bold text-gray-700 dark:text-gray-300">
            Items Stored Here ({{ displayedItems.length }})
          </h3>
          <span v-if="selectedLocationId" @click="selectedLocationId = null" class="text-xs text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer font-medium">
            Clear filter (Show All)
          </span>
        </div>

        <div v-if="loading" class="text-center py-12 text-gray-400 text-sm">Loading inventory...</div>
        <div v-else-if="displayedItems.length === 0" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-8 text-center text-gray-500 dark:text-gray-400 text-xs sm:text-sm">
          No items found in this container. Click "Store Item" to add something.
        </div>

        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          <div
            v-for="item in displayedItems"
            :key="item.id"
            class="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-100 dark:border-gray-800 p-3.5 sm:p-4 flex flex-col justify-between hover:border-indigo-200 dark:hover:border-indigo-800 transition"
          >
            <div>
              <div class="flex items-start justify-between gap-2 mb-1.5">
                <h3
                  @click="selectedItem = item; showDetailsModal = true"
                  class="font-semibold text-gray-900 dark:text-gray-100 leading-tight hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer text-sm sm:text-base"
                >
                  {{ item.name }}
                </h3>
                <span
                  class="text-[11px] sm:text-xs px-2 py-0.5 rounded font-medium shrink-0"
                  :class="item.is_consumable ? 'bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800' : 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800'"
                >
                  Qty: {{ item.quantity }}
                </span>
              </div>

              <div v-if="item.qr_code" class="flex items-center gap-1 text-[11px] text-gray-400 font-mono mb-2">
                <QrCode class="w-3 h-3" />
                <span>{{ item.qr_code }}</span>
              </div>

              <p class="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mb-3">
                {{ item.description || "No description provided." }}
              </p>

              <div v-if="item.metadata_fields && Object.keys(item.metadata_fields).length" class="flex flex-wrap gap-1 mb-3">
                <span
                  v-for="(val, key) in item.metadata_fields"
                  :key="key"
                  class="text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 px-1.5 py-0.5 rounded"
                >
                  <strong>{{ key }}:</strong> {{ val }}
                </span>
              </div>
            </div>

            <div class="border-t border-gray-50 dark:border-gray-800 pt-2.5 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span class="flex items-center gap-1 text-gray-600 dark:text-gray-400 font-medium truncate max-w-[120px] sm:max-w-[140px]" :title="getLocationBreadcrumbs(item.location_id).map(c=>c.name).join(' > ')">
                <MapPin class="w-3.5 h-3.5 text-gray-400 shrink-0" />
                <span class="truncate">
                  {{ getLocationBreadcrumbs(item.location_id).map(c => c.name).join(' > ') || 'Unassigned' }}
                </span>
              </span>

              <div class="flex items-center gap-1">
                <a
                  v-if="item.source_url"
                  :href="item.source_url"
                  target="_blank"
                  class="p-1 hover:text-indigo-600 dark:hover:text-indigo-400 rounded transition"
                  title="Source URL"
                >
                  <ExternalLink class="w-3.5 h-3.5" />
                </a>
                <button
                  @click="openEditItemModal(item)"
                  class="p-1 hover:text-blue-600 dark:hover:text-blue-400 rounded transition cursor-pointer"
                  title="Edit item"
                >
                  <Pencil class="w-3.5 h-3.5" />
                </button>
                <button
                  v-if="systemSettings.print_enabled"
                  @click="printItemLabel(item.id)"
                  class="p-1 hover:text-indigo-600 dark:hover:text-indigo-400 rounded transition cursor-pointer"
                  title="Print label via Web Bluetooth"
                >
                  <Printer class="w-3.5 h-3.5" />
                </button>
                <button
                  @click="handleDeleteItem(item.id)"
                  class="p-1 hover:text-red-600 dark:hover:text-red-400 rounded transition cursor-pointer"
                  title="Delete item"
                >
                  <Trash2 class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>

    <div
      v-if="showSettingsModal"
      class="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 z-50 overflow-y-auto"
    >
      <div class="bg-white dark:bg-gray-900 rounded-2xl shadow-xl max-w-md w-full p-4 sm:p-6 space-y-4 my-auto border dark:border-gray-800 transition-colors">
        <div class="flex justify-between items-center">
          <h3 class="text-base sm:text-lg font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <Settings class="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            <span>Settings & Preferences</span>
          </h3>
          <button @click="showSettingsModal = false" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer">
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="space-y-4">
          <div v-if="installPromptEvent" class="bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 p-3 rounded-xl flex items-center justify-between">
            <div>
              <p class="text-xs font-bold text-indigo-950 dark:text-indigo-200">Install HomeStack App</p>
              <p class="text-[10px] text-indigo-600 dark:text-indigo-400">Add to home screen for fullscreen app experience</p>
            </div>
            <button
              @click="installPwa"
              class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg flex items-center gap-1.5 cursor-pointer shadow-xs transition"
            >
              <Download class="w-3.5 h-3.5" />
              <span>Install</span>
            </button>
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Display Theme</label>
            <div class="grid grid-cols-3 gap-2">
              <button
                type="button"
                @click="applyTheme('light')"
                class="p-2.5 border rounded-xl flex flex-col items-center gap-1.5 transition cursor-pointer"
                :class="currentTheme === 'light' ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-bold ring-2 ring-indigo-500/20' : 'border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-700'"
              >
                <Sun class="w-4 h-4" />
                <span class="text-xs">Light</span>
              </button>

              <button
                type="button"
                @click="applyTheme('dark')"
                class="p-2.5 border rounded-xl flex flex-col items-center gap-1.5 transition cursor-pointer"
                :class="currentTheme === 'dark' ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-bold ring-2 ring-indigo-500/20' : 'border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-700'"
              >
                <Moon class="w-4 h-4" />
                <span class="text-xs">Dark</span>
              </button>

              <button
                type="button"
                @click="applyTheme('system')"
                class="p-2.5 border rounded-xl flex flex-col items-center gap-1.5 transition cursor-pointer"
                :class="currentTheme === 'system' ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-bold ring-2 ring-indigo-500/20' : 'border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-700'"
              >
                <Laptop class="w-4 h-4" />
                <span class="text-xs">System</span>
              </button>
            </div>
          </div>

          <div class="border-t border-gray-100 dark:border-gray-800 pt-3 space-y-3">
            <div>
              <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Gemini API Key</label>
              <input
                v-model="settingsForm.gemini_api_key"
                type="password"
                placeholder="Paste your API key (AIzaSy...)"
                class="w-full text-xs sm:text-sm border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none font-mono"
              />
            </div>

          <div class="border-t border-gray-100 dark:border-gray-800 pt-4 space-y-4">
            <div class="flex items-center justify-between">
              <label class="text-sm font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                <Printer class="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                Hardware Printing
              </label>
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" v-model="settingsForm.print_enabled" class="sr-only peer">
                <div class="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-indigo-300 dark:peer-focus:ring-indigo-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:border-gray-600 peer-checked:bg-indigo-600"></div>
              </label>
            </div>

            <div v-if="settingsForm.print_enabled" class="space-y-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-100 dark:border-gray-800">
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wide mb-1">Connection</label>
                  <select v-model="settingsForm.printer_transport" class="w-full text-xs border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded-lg p-2 outline-none">
                    <option value="browser">System Browser (PDF)</option>
                    <option value="ble">Web Bluetooth</option>
                    <option value="network">Network (Wi-Fi/LAN)</option>
                  </select>
                </div>
                <div>
                  <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wide mb-1">Language/Brand</label>
                  <select v-model="settingsForm.printer_language" class="w-full text-xs border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded-lg p-2 outline-none">
                    <option value="pdf">Generic PDF</option>
                    <option value="fichero">Fichero / Niimbot D11</option>
                    <option value="escpos">Standard ESC/POS</option>
                    <option value="tspl">TSPL (Phomemo/TSC)</option>
                  </select>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wide mb-1">Width (mm)</label>
                  <input v-model.number="settingsForm.label_width" type="number" class="w-full text-xs border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded-lg p-2 outline-none" />
                </div>
                <div>
                  <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wide mb-1">Height (mm)</label>
                  <input v-model.number="settingsForm.label_height" type="number" class="w-full text-xs border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded-lg p-2 outline-none" />
                </div>
              </div>

              <div v-if="settingsForm.printer_transport === 'ble'">
                <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wide mb-1">Bluetooth Prefixes (comma separated)</label>
                <input v-model="settingsForm.printer_ble_name_prefix" placeholder="FICHERO,D11" class="w-full text-xs border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded-lg p-2 outline-none" />
              </div>

              <div v-if="settingsForm.printer_transport === 'network'">
                <label class="block text-[10px] font-bold text-gray-500 uppercase tracking-wide mb-1">Printer IP Address</label>
                <input v-model="settingsForm.printer_ip" placeholder="192.168.1.X:9100" class="w-full text-xs border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded-lg p-2 outline-none" />
              </div>
            </div>
          </div>

            <div>
              <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Gemini Model</label>
              <select
                v-model="settingsForm.gemini_model"
                class="w-full text-xs sm:text-sm border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
              >
                <option v-for="model in availableModels" :key="model" :value="model">
                  {{ model }}
                </option>
              </select>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-3 border-t border-gray-100 dark:border-gray-800">
          <button @click="showSettingsModal = false" class="px-3 sm:px-4 py-2 text-xs sm:text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg cursor-pointer">
            Cancel
          </button>
          <button
            @click="saveSettings"
            :disabled="settingsSaving"
            class="px-4 py-2 text-xs sm:text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium cursor-pointer flex items-center gap-1.5"
          >
            <Loader2 v-if="settingsSaving" class="w-4 h-4 animate-spin" />
            <span>Save Configuration</span>
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="showLocationModal"
      class="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 z-50 overflow-y-auto"
    >
      <div class="bg-white dark:bg-gray-900 rounded-2xl shadow-xl max-w-lg w-full p-4 sm:p-6 space-y-4 my-auto max-h-[92vh] overflow-y-auto border dark:border-gray-800 transition-colors">
        <div class="flex justify-between items-center">
          <h3 class="text-base sm:text-lg font-bold text-gray-900 dark:text-gray-100">
            {{ editingLocationId ? "Edit Storage Container" : "Create Storage Container" }}
          </h3>
          <button @click="showLocationModal = false" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer">
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="space-y-3.5">
          <div>
            <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">Select Container Type</label>
            <div class="grid grid-cols-2 gap-2">
              <div
                @click="locationForm.location_type = 'room'"
                class="p-2.5 border rounded-xl cursor-pointer transition flex items-center gap-2"
                :class="locationForm.location_type === 'room' ? 'border-purple-600 bg-purple-50/70 dark:bg-purple-950/60 ring-2 ring-purple-600/20' : 'border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700'"
              >
                <Home class="w-4 h-4 text-purple-600 dark:text-purple-400 shrink-0" />
                <div>
                  <p class="text-xs font-bold text-gray-900 dark:text-gray-100">Room</p>
                  <p class="text-[10px] text-gray-500 dark:text-gray-400">Lab, Garage</p>
                </div>
              </div>

              <div
                @click="locationForm.location_type = 'shelf'"
                class="p-2.5 border rounded-xl cursor-pointer transition flex items-center gap-2"
                :class="locationForm.location_type === 'shelf' ? 'border-blue-600 bg-blue-50/70 dark:bg-blue-950/60 ring-2 ring-blue-600/20' : 'border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700'"
              >
                <Grid class="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" />
                <div>
                  <p class="text-xs font-bold text-gray-900 dark:text-gray-100">Shelf / Rack</p>
                  <p class="text-[10px] text-gray-500 dark:text-gray-400">Rack, Cabinet</p>
                </div>
              </div>

              <div
                @click="locationForm.location_type = 'box'"
                class="p-2.5 border rounded-xl cursor-pointer transition flex items-center gap-2"
                :class="locationForm.location_type === 'box' ? 'border-emerald-600 bg-emerald-50/70 dark:bg-emerald-950/60 ring-2 ring-emerald-600/20' : 'border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700'"
              >
                <Box class="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <div>
                  <p class="text-xs font-bold text-gray-900 dark:text-gray-100">Box / Bin</p>
                  <p class="text-[10px] text-gray-500 dark:text-gray-400">Plastic container</p>
                </div>
              </div>

              <div
                @click="locationForm.location_type = 'drawer'"
                class="p-2.5 border rounded-xl cursor-pointer transition flex items-center gap-2"
                :class="locationForm.location_type === 'drawer' ? 'border-amber-600 bg-amber-50/70 dark:bg-amber-950/60 ring-2 ring-amber-600/20' : 'border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700'"
              >
                <Inbox class="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
                <div>
                  <p class="text-xs font-bold text-gray-900 dark:text-gray-100">Drawer / Slot</p>
                  <p class="text-[10px] text-gray-500 dark:text-gray-400">Small organizer</p>
                </div>
              </div>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Container Name *</label>
            <input
              v-model="locationForm.name"
              placeholder="e.g. Box #12 - Screws, Shelf A, Lab"
              class="w-full text-xs sm:text-sm border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Placed Inside (Nesting Parent)</label>
            <select
              v-model="locationForm.parent_id"
              class="w-full text-xs sm:text-sm border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
            >
              <option :value="null">None (Standalone / Root)</option>
              <option
                v-for="loc in locations.filter(l => l.id !== editingLocationId)"
                :key="loc.id"
                :value="loc.id"
              >
                Inside: {{ getLocationBreadcrumbs(loc.id).map(c=>c.name).join(' > ') }} ({{ loc.location_type }})
              </option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Description (Optional)</label>
            <input
              v-model="locationForm.description"
              placeholder="Notes or dimensions"
              class="w-full text-xs sm:text-sm border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-3 border-t border-gray-100 dark:border-gray-800">
          <button @click="showLocationModal = false" class="px-3 sm:px-4 py-2 text-xs sm:text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg cursor-pointer">
            Cancel
          </button>
          <button @click="submitLocation" class="px-3 sm:px-4 py-2 text-xs sm:text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-semibold cursor-pointer">
            {{ editingLocationId ? "Update Container" : "Create Container" }}
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="showQrScannerModal"
      class="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 z-50"
    >
      <div class="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-sm sm:max-w-md w-full p-4 sm:p-6 space-y-4 border dark:border-gray-800">
        <div class="flex justify-between items-center">
          <h3 class="text-base sm:text-lg font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <ScanLine class="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            <span>Scan QR Code</span>
          </h3>
          <button @click="stopQrScanner" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer">
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="rounded-xl overflow-hidden bg-black flex items-center justify-center min-h-[260px] sm:min-h-[300px]">
          <div id="qr-camera-viewport" class="w-full"></div>
        </div>

        <p class="text-xs text-center text-gray-500 dark:text-gray-400">
          Point camera at an Item or Box QR label.
        </p>

        <button
          @click="stopQrScanner"
          class="w-full py-2.5 text-xs sm:text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-medium rounded-lg cursor-pointer"
        >
          Cancel
        </button>
      </div>
    </div>

    <div
      v-if="showBoxContentsModal && selectedLocation"
      class="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 z-50 overflow-y-auto"
    >
      <div class="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-lg w-full p-4 sm:p-6 space-y-4 my-auto max-h-[92vh] overflow-y-auto border dark:border-gray-800 transition-colors">
        <div class="flex justify-between items-start">
          <div class="flex items-center gap-2.5">
            <div class="p-2 sm:p-3 rounded-xl border" :class="getLocationTypeBadgeClass(selectedLocation.location_type)">
              <component :is="getLocationIcon(selectedLocation.location_type)" class="w-5 h-5 sm:w-6 sm:h-6" />
            </div>
            <div>
              <span class="text-[11px] font-mono text-gray-400">{{ selectedLocation.qr_code }}</span>
              <h3 class="text-base sm:text-lg font-bold text-gray-900 dark:text-gray-100">{{ selectedLocation.name }}</h3>
              <p class="text-xs text-indigo-600 dark:text-indigo-400 font-medium">
                {{ getLocationBreadcrumbs(selectedLocation.id).map(c=>c.name).join(' > ') }}
              </p>
            </div>
          </div>
          <button @click="showBoxContentsModal = false" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer">
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="border-t border-b border-gray-100 dark:border-gray-800 py-3">
          <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
            Items Inside ({{ boxContainedItems.length }})
          </h4>

          <div v-if="boxContainedItems.length === 0" class="text-center py-6 text-gray-400 text-xs sm:text-sm">
            This container is currently empty.
          </div>

          <div v-else class="space-y-2 max-h-52 overflow-y-auto pr-1">
            <div
              v-for="item in boxContainedItems"
              :key="item.id"
              @click="selectedItem = item; showBoxContentsModal = false; showDetailsModal = true"
              class="flex items-center justify-between p-2.5 bg-gray-50 dark:bg-gray-800/60 hover:bg-indigo-50/50 dark:hover:bg-indigo-950/40 rounded-xl cursor-pointer transition border border-gray-100 dark:border-gray-800"
            >
              <div>
                <p class="text-xs sm:text-sm font-semibold text-gray-900 dark:text-gray-100">{{ item.name }}</p>
                <p class="text-[10px] text-gray-400">{{ item.qr_code }}</p>
              </div>
              <span class="text-xs font-bold bg-white dark:bg-gray-900 px-2 py-0.5 rounded border border-gray-200 dark:border-gray-700">
                Qty: {{ item.quantity }}
              </span>
            </div>
          </div>
        </div>

        <div class="flex justify-between items-center pt-2">
          <button
            @click="selectedLocationId = selectedLocation.id; showBoxContentsModal = false"
            class="text-xs text-indigo-600 dark:text-indigo-400 hover:underline font-semibold"
          >
            Filter to Container
          </button>
          <button
            v-if="systemSettings.print_enabled"
            @click="printLocationLabel(selectedLocation.id)"
            class="px-3 sm:px-4 py-2 text-xs sm:text-sm bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg flex items-center gap-1.5 cursor-pointer"
          >
            <Printer class="w-4 h-4" /> Print Box Label
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="showDetailsModal && selectedItem"
      class="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 z-50 overflow-y-auto"
    >
      <div class="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-lg w-full p-4 sm:p-6 space-y-4 my-auto max-h-[92vh] overflow-y-auto border dark:border-gray-800 transition-colors">
        <div class="flex justify-between items-start">
          <div>
            <div class="flex items-center gap-1.5 mb-1">
              <span class="text-xs font-mono bg-indigo-50 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 px-2 py-0.5 rounded font-semibold">
                {{ selectedItem.qr_code }}
              </span>
              <span
                class="text-xs px-2 py-0.5 rounded font-medium"
                :class="selectedItem.is_consumable ? 'bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800' : 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800'"
              >
                {{ selectedItem.is_consumable ? 'Consumable' : 'Asset' }}
              </span>
            </div>
            <h3 class="text-lg sm:text-xl font-bold text-gray-900 dark:text-gray-100">{{ selectedItem.name }}</h3>
          </div>
          <button @click="showDetailsModal = false" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer">
            <X class="w-5 h-5" />
          </button>
        </div>

        <p class="text-xs sm:text-sm text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-800/60 p-2.5 sm:p-3 rounded-lg border border-transparent dark:border-gray-800">
          {{ selectedItem.description || "No description provided." }}
        </p>

        <div class="grid grid-cols-2 gap-2 sm:gap-3">
          <div class="border border-gray-100 dark:border-gray-800 p-2.5 sm:p-3 rounded-xl bg-gray-50/50 dark:bg-gray-800/40">
            <span class="text-[11px] text-gray-400 flex items-center gap-1 mb-1">
              <MapPin class="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" /> Location Hierarchy
            </span>
            <p class="text-xs font-semibold text-gray-800 dark:text-gray-200 leading-snug">
              {{ getLocationBreadcrumbs(selectedItem.location_id).map(c=>c.name).join(' > ') || 'Unassigned' }}
            </p>
          </div>

          <div class="border border-gray-100 dark:border-gray-800 p-2.5 sm:p-3 rounded-xl bg-gray-50/50 dark:bg-gray-800/40 flex flex-col justify-between">
            <span class="text-[11px] text-gray-400 mb-1">Stock Quantity</span>
            <div class="flex items-center justify-between">
              <button
                @click="adjustQuantity(-1)"
                class="w-7 h-7 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg flex items-center justify-center font-bold text-gray-600 dark:text-gray-200 cursor-pointer"
              >
                <Minus class="w-3.5 h-3.5" />
              </button>
              <span class="text-sm sm:text-base font-bold text-gray-900 dark:text-gray-100">{{ selectedItem.quantity }}</span>
              <button
                @click="adjustQuantity(1)"
                class="w-7 h-7 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg flex items-center justify-center font-bold text-gray-600 dark:text-gray-200 cursor-pointer"
              >
                <Plus class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        <div v-if="selectedItem.metadata_fields && Object.keys(selectedItem.metadata_fields).length">
          <label class="block text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1.5">Specifications</label>
          <div class="grid grid-cols-2 gap-2">
            <div
              v-for="(val, key) in selectedItem.metadata_fields"
              :key="key"
              class="bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800 p-2 rounded-lg text-xs"
            >
              <span class="text-gray-400 block capitalize text-[10px]">{{ key }}</span>
              <span class="font-medium text-gray-800 dark:text-gray-200 break-words">{{ val }}</span>
            </div>
          </div>
        </div>

        <div class="flex justify-between items-center pt-3 border-t border-gray-100 dark:border-gray-800">
          <button
            @click="handleDeleteItem(selectedItem.id)"
            class="text-xs text-red-600 hover:text-red-800 dark:hover:text-red-400 font-medium flex items-center gap-1 cursor-pointer"
          >
            <Trash2 class="w-3.5 h-3.5" /> Delete
          </button>
          <div class="flex gap-2">
            <button
              @click="openEditItemModal(selectedItem)"
              class="px-3 sm:px-4 py-2 text-xs sm:text-sm bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-medium rounded-lg cursor-pointer"
            >
              Edit
            </button>
            <button
              v-if="systemSettings.print_enabled"
              @click="printItemLabel(selectedItem.id)"
              class="px-3 sm:px-4 py-2 text-xs sm:text-sm bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg flex items-center gap-1.5 cursor-pointer"
            >
              <Printer class="w-4 h-4" /> Print Label
            </button>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="showItemModal"
      class="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-4 z-50 overflow-y-auto"
    >
      <div class="bg-white dark:bg-gray-900 rounded-2xl shadow-xl max-w-xl w-full p-4 sm:p-6 space-y-4 my-auto max-h-[92vh] overflow-y-auto border dark:border-gray-800 transition-colors">
        <div class="flex justify-between items-center">
          <h3 class="text-base sm:text-lg font-bold text-gray-900 dark:text-gray-100">
            {{ editingItemId ? "Edit Item" : "Add New Item" }}
          </h3>
          <button @click="showItemModal = false" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer">
            <X class="w-5 h-5" />
          </button>
        </div>

        <div
          v-if="!editingItemId"
          class="bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-900 rounded-xl p-3 sm:p-4 flex items-center justify-between"
        >
          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 bg-indigo-600 dark:bg-indigo-500 text-white rounded-lg flex items-center justify-center shrink-0">
              <Camera v-if="!aiLoading" class="w-4 h-4" />
              <Loader2 v-else class="w-4 h-4 animate-spin" />
            </div>
            <div>
              <p class="text-xs sm:text-sm font-semibold text-indigo-950 dark:text-indigo-200">AI Magic Fill</p>
              <p class="text-[10px] sm:text-xs text-indigo-600 dark:text-indigo-400">Snap a photo to fill details</p>
            </div>
          </div>

          <label class="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium px-3 py-1.5 sm:py-2 rounded-lg cursor-pointer transition shrink-0">
            <span>{{ aiLoading ? "Analyzing..." : "Scan Photo" }}</span>
            <input
              type="file"
              accept="image/*"
              capture="environment"
              class="hidden"
              @change="handleImageUpload"
              :disabled="aiLoading"
            />
          </label>
        </div>

        <div class="space-y-3">
          <div>
            <label class="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Item Name *</label>
            <input
              v-model="itemForm.name"
              placeholder="e.g. Ceramic Capacitor 100nF"
              class="w-full text-xs sm:text-sm border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Description</label>
            <textarea
              v-model="itemForm.description"
              rows="2"
              placeholder="Description or notes"
              class="w-full text-xs sm:text-sm border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
            ></textarea>
          </div>

          <div class="grid grid-cols-2 gap-2.5">
            <div>
              <label class="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Store Inside</label>
              <select
                v-model="itemForm.location_id"
                class="w-full text-xs sm:text-sm border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
              >
                <option :value="null">Unassigned</option>
                <option v-for="loc in locations" :key="loc.id" :value="loc.id">
                  {{ getLocationBreadcrumbs(loc.id).map(c=>c.name).join(' > ') }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Quantity</label>
              <input
                v-model.number="itemForm.quantity"
                type="number"
                min="0"
                class="w-full text-xs sm:text-sm border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="consumable"
              v-model="itemForm.is_consumable"
              class="rounded text-indigo-600 focus:ring-indigo-500"
            />
            <label for="consumable" class="text-xs text-gray-700 dark:text-gray-300 font-medium">Is Consumable / Bulk component?</label>
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Source / Purchase URL</label>
            <input
              v-model="itemForm.source_url"
              placeholder="https://..."
              class="w-full text-xs sm:text-sm border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>

          <div class="border-t border-gray-100 dark:border-gray-800 pt-2.5">
            <label class="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Custom Attributes</label>
            <div class="flex flex-wrap gap-1 mb-2">
              <span
                v-for="(val, key) in itemForm.metadata_fields"
                :key="key"
                class="inline-flex items-center gap-1 text-[11px] bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 px-2 py-0.5 rounded-md"
              >
                <span><strong>{{ key }}:</strong> {{ val }}</span>
                <button @click="removeMetadataField(key)" class="hover:text-red-500 cursor-pointer">
                  <X class="w-3 h-3" />
                </button>
              </span>
            </div>

            <div class="flex gap-1.5">
              <input v-model="customMetaKey" placeholder="Key (e.g. Voltage)" class="w-1/3 text-xs border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg p-1.5 outline-none" />
              <input v-model="customMetaValue" placeholder="Value (e.g. 5V)" class="w-1/2 text-xs border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg p-1.5 outline-none" />
              <button @click="addCustomMetadata" type="button" class="bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-xs px-2.5 rounded-lg font-medium cursor-pointer">
                Add
              </button>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-3 border-t border-gray-100 dark:border-gray-800">
          <button @click="showItemModal = false" class="px-3 sm:px-4 py-2 text-xs sm:text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg cursor-pointer">
            Cancel
          </button>
          <button @click="submitItem(false)" class="px-3 sm:px-4 py-2 text-xs sm:text-sm bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 rounded-lg hover:bg-black dark:hover:bg-white cursor-pointer font-semibold">
            {{ editingItemId ? "Update Item" : "Save Item" }}
          </button>
          <button v-if="systemSettings.print_enabled" @click="submitItem(true)" class="px-3 sm:px-4 py-2 text-xs sm:text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center gap-1.5 cursor-pointer font-semibold">
            <Printer class="w-4 h-4" />
            <span>{{ editingItemId ? "Update & Print" : "Save & Print" }}</span>
          </button>
        </div>
      </div>
    </div>

  </div>
</template>