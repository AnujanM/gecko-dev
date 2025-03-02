/* -*- Mode: C++; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set ts=8 sts=2 et sw=2 tw=80: */
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

#ifndef mozilla_dom_idbobjectstore_h__
#define mozilla_dom_idbobjectstore_h__

#include "js/RootingAPI.h"
#include "mozilla/dom/IDBCursorBinding.h"
#include "mozilla/dom/IDBIndexBinding.h"
#include "nsAutoPtr.h"
#include "nsCycleCollectionParticipant.h"
#include "nsISupports.h"
#include "nsString.h"
#include "nsTArray.h"
#include "nsWrapperCache.h"

struct JSClass;
class nsIGlobalObject;

namespace mozilla {

class ErrorResult;

namespace dom {

class DOMStringList;
class IDBCursor;
class IDBRequest;
class IDBTransaction;
class StringOrStringSequence;
template <typename>
class Sequence;

namespace indexedDB {
class Key;
class KeyPath;
class IndexUpdateInfo;
class ObjectStoreSpec;
struct StructuredCloneReadInfo;
}  // namespace indexedDB

class IDBObjectStore final : public nsISupports, public nsWrapperCache {
  typedef indexedDB::IndexUpdateInfo IndexUpdateInfo;
  typedef indexedDB::Key Key;
  typedef indexedDB::KeyPath KeyPath;
  typedef indexedDB::ObjectStoreSpec ObjectStoreSpec;
  typedef indexedDB::StructuredCloneReadInfo StructuredCloneReadInfo;

  // For AddOrPut() and DeleteInternal().
  friend class IDBCursor;

  static const JSClass sDummyPropJSClass;

  // TODO: This could be made const if Bug 1575173 is resolved. It is
  // initialized in the constructor and never modified/cleared.
  RefPtr<IDBTransaction> mTransaction;
  JS::Heap<JS::Value> mCachedKeyPath;

  // This normally points to the ObjectStoreSpec owned by the parent IDBDatabase
  // object. However, if this objectStore is part of a versionchange transaction
  // and it gets deleted then the spec is copied into mDeletedSpec and mSpec is
  // set to point at mDeletedSpec.
  const ObjectStoreSpec* mSpec;
  nsAutoPtr<ObjectStoreSpec> mDeletedSpec;

  nsTArray<RefPtr<IDBIndex>> mIndexes;
  nsTArray<RefPtr<IDBIndex>> mDeletedIndexes;

  const int64_t mId;
  bool mRooted;

 public:
  struct StructuredCloneWriteInfo;
  struct StructuredCloneInfo;

  class MOZ_STACK_CLASS ValueWrapper final {
    JS::Rooted<JS::Value> mValue;
    bool mCloned;

   public:
    ValueWrapper(JSContext* aCx, JS::Handle<JS::Value> aValue)
        : mValue(aCx, aValue), mCloned(false) {
      MOZ_COUNT_CTOR(IDBObjectStore::ValueWrapper);
    }

    ~ValueWrapper() { MOZ_COUNT_DTOR(IDBObjectStore::ValueWrapper); }

    const JS::Rooted<JS::Value>& Value() const { return mValue; }

    bool Clone(JSContext* aCx);
  };

  static already_AddRefed<IDBObjectStore> Create(IDBTransaction* aTransaction,
                                                 const ObjectStoreSpec& aSpec);

  static void AppendIndexUpdateInfo(int64_t aIndexID, const KeyPath& aKeyPath,
                                    bool aMultiEntry, const nsCString& aLocale,
                                    JSContext* aCx, JS::Handle<JS::Value> aVal,
                                    nsTArray<IndexUpdateInfo>* aUpdateInfoArray,
                                    ErrorResult* aRv);

  static void DeserializeIndexValueToUpdateInfos(
      int64_t aIndexID, const KeyPath& aKeyPath, bool aMultiEntry,
      const nsCString& aLocale, StructuredCloneReadInfo& aCloneReadInfo,
      nsTArray<IndexUpdateInfo>& aUpdateInfoArray, ErrorResult& aRv);

  static void ClearCloneReadInfo(StructuredCloneReadInfo& aReadInfo);

  static bool DeserializeValue(JSContext* aCx,
                               StructuredCloneReadInfo& aCloneReadInfo,
                               JS::MutableHandle<JS::Value> aValue);

  static nsresult DeserializeUpgradeValueToFileIds(
      StructuredCloneReadInfo& aCloneReadInfo, nsAString& aFileIds);

  static const JSClass* DummyPropClass() { return &sDummyPropJSClass; }

  void AssertIsOnOwningThread() const
#ifdef DEBUG
      ;
#else
  {
  }
#endif

  int64_t Id() const {
    AssertIsOnOwningThread();

    return mId;
  }

  const nsString& Name() const;

  bool AutoIncrement() const;

  const KeyPath& GetKeyPath() const;

  bool HasValidKeyPath() const;

  nsIGlobalObject* GetParentObject() const;

  void GetName(nsString& aName) const {
    AssertIsOnOwningThread();

    aName = Name();
  }

  void SetName(const nsAString& aName, ErrorResult& aRv);

  void GetKeyPath(JSContext* aCx, JS::MutableHandle<JS::Value> aResult,
                  ErrorResult& aRv);

  already_AddRefed<DOMStringList> IndexNames();

  IDBTransaction* Transaction() const {
    AssertIsOnOwningThread();

    return mTransaction;
  }

  already_AddRefed<IDBRequest> Add(JSContext* aCx, JS::Handle<JS::Value> aValue,
                                   JS::Handle<JS::Value> aKey,
                                   ErrorResult& aRv) {
    AssertIsOnOwningThread();

    ValueWrapper valueWrapper(aCx, aValue);

    return AddOrPut(aCx, valueWrapper, aKey, false, /* aFromCursor */ false,
                    aRv);
  }

  already_AddRefed<IDBRequest> Put(JSContext* aCx, JS::Handle<JS::Value> aValue,
                                   JS::Handle<JS::Value> aKey,
                                   ErrorResult& aRv) {
    AssertIsOnOwningThread();

    ValueWrapper valueWrapper(aCx, aValue);

    return AddOrPut(aCx, valueWrapper, aKey, true, /* aFromCursor */ false,
                    aRv);
  }

  already_AddRefed<IDBRequest> Delete(JSContext* aCx,
                                      JS::Handle<JS::Value> aKey,
                                      ErrorResult& aRv) {
    AssertIsOnOwningThread();

    return DeleteInternal(aCx, aKey, /* aFromCursor */ false, aRv);
  }

  already_AddRefed<IDBRequest> Get(JSContext* aCx, JS::Handle<JS::Value> aKey,
                                   ErrorResult& aRv) {
    AssertIsOnOwningThread();

    return GetInternal(/* aKeyOnly */ false, aCx, aKey, aRv);
  }

  already_AddRefed<IDBRequest> GetKey(JSContext* aCx,
                                      JS::Handle<JS::Value> aKey,
                                      ErrorResult& aRv) {
    AssertIsOnOwningThread();

    return GetInternal(/* aKeyOnly */ true, aCx, aKey, aRv);
  }

  already_AddRefed<IDBRequest> Clear(JSContext* aCx, ErrorResult& aRv);

  already_AddRefed<IDBIndex> CreateIndex(
      const nsAString& aName, const StringOrStringSequence& aKeyPath,
      const IDBIndexParameters& aOptionalParameters, ErrorResult& aRv);

  already_AddRefed<IDBIndex> Index(const nsAString& aName, ErrorResult& aRv);

  void DeleteIndex(const nsAString& aName, ErrorResult& aRv);

  already_AddRefed<IDBRequest> Count(JSContext* aCx, JS::Handle<JS::Value> aKey,
                                     ErrorResult& aRv);

  already_AddRefed<IDBRequest> GetAll(JSContext* aCx,
                                      JS::Handle<JS::Value> aKey,
                                      const Optional<uint32_t>& aLimit,
                                      ErrorResult& aRv) {
    AssertIsOnOwningThread();

    return GetAllInternal(/* aKeysOnly */ false, aCx, aKey, aLimit, aRv);
  }

  already_AddRefed<IDBRequest> GetAllKeys(JSContext* aCx,
                                          JS::Handle<JS::Value> aKey,
                                          const Optional<uint32_t>& aLimit,
                                          ErrorResult& aRv) {
    AssertIsOnOwningThread();

    return GetAllInternal(/* aKeysOnly */ true, aCx, aKey, aLimit, aRv);
  }

  already_AddRefed<IDBRequest> OpenCursor(JSContext* aCx,
                                          JS::Handle<JS::Value> aRange,
                                          IDBCursorDirection aDirection,
                                          ErrorResult& aRv) {
    AssertIsOnOwningThread();

    return OpenCursorInternal(/* aKeysOnly */ false, aCx, aRange, aDirection,
                              aRv);
  }

  already_AddRefed<IDBRequest> OpenCursor(JSContext* aCx,
                                          IDBCursorDirection aDirection,
                                          ErrorResult& aRv) {
    AssertIsOnOwningThread();

    return OpenCursorInternal(/* aKeysOnly */ false, aCx,
                              JS::UndefinedHandleValue, aDirection, aRv);
  }

  already_AddRefed<IDBRequest> OpenKeyCursor(JSContext* aCx,
                                             JS::Handle<JS::Value> aRange,
                                             IDBCursorDirection aDirection,
                                             ErrorResult& aRv) {
    AssertIsOnOwningThread();

    return OpenCursorInternal(/* aKeysOnly */ true, aCx, aRange, aDirection,
                              aRv);
  }

  void RefreshSpec(bool aMayDelete);

  const ObjectStoreSpec& Spec() const;

  void NoteDeletion();

  bool IsDeleted() const {
    AssertIsOnOwningThread();

    return !!mDeletedSpec;
  }

  NS_DECL_CYCLE_COLLECTING_ISUPPORTS
  NS_DECL_CYCLE_COLLECTION_SCRIPT_HOLDER_CLASS(IDBObjectStore)

  // nsWrapperCache
  virtual JSObject* WrapObject(JSContext* aCx,
                               JS::Handle<JSObject*> aGivenProto) override;

 private:
  IDBObjectStore(IDBTransaction* aTransaction, const ObjectStoreSpec* aSpec);

  ~IDBObjectStore();

  void GetAddInfo(JSContext* aCx, ValueWrapper& aValueWrapper,
                  JS::Handle<JS::Value> aKeyVal,
                  StructuredCloneWriteInfo& aCloneWriteInfo, Key& aKey,
                  nsTArray<IndexUpdateInfo>& aUpdateInfoArray,
                  ErrorResult& aRv);

  already_AddRefed<IDBRequest> AddOrPut(JSContext* aCx,
                                        ValueWrapper& aValueWrapper,
                                        JS::Handle<JS::Value> aKey,
                                        bool aOverwrite, bool aFromCursor,
                                        ErrorResult& aRv);

  already_AddRefed<IDBRequest> DeleteInternal(JSContext* aCx,
                                              JS::Handle<JS::Value> aKey,
                                              bool aFromCursor,
                                              ErrorResult& aRv);

  already_AddRefed<IDBRequest> GetInternal(bool aKeyOnly, JSContext* aCx,
                                           JS::Handle<JS::Value> aKey,
                                           ErrorResult& aRv);

  already_AddRefed<IDBRequest> GetAllInternal(bool aKeysOnly, JSContext* aCx,
                                              JS::Handle<JS::Value> aKey,
                                              const Optional<uint32_t>& aLimit,
                                              ErrorResult& aRv);

  already_AddRefed<IDBRequest> OpenCursorInternal(bool aKeysOnly,
                                                  JSContext* aCx,
                                                  JS::Handle<JS::Value> aRange,
                                                  IDBCursorDirection aDirection,
                                                  ErrorResult& aRv);
};

}  // namespace dom
}  // namespace mozilla

#endif  // mozilla_dom_idbobjectstore_h__
