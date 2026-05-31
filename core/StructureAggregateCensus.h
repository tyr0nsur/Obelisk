#pragma once

#include "StructureEventDispatcher.h"

#include <array>
#include <cstddef>
#include <cstdint>

namespace Obelisk::Core
{
    struct StructureAggregateCensusOptions
    {
        bool Enabled = false;
        size_t WindowEventLimit = 0;
        size_t VariantBucketLimit = 0;
    };

    struct StructureAggregateCensusFieldCounters
    {
        size_t Present = 0;
        size_t BoolTrue = 0;
        size_t BoolFalse = 0;
        size_t Int32Present = 0;
    };

    struct StructureAggregateCensusVariantBucket
    {
        int32_t Value = 0;
        size_t Count = 0;
        bool Used = false;
    };

    struct StructureAggregateCensusSnapshot
    {
        size_t WindowEventLimit = 0;
        size_t VariantBucketLimit = 0;
        size_t WindowEventsSeen = 0;
        size_t MatchedTotal = 0;
        size_t OriginalCalledTotal = 0;
        size_t OriginalBlockedTotal = 0;
        size_t RejectedSensitiveOrNonStructure = 0;
        size_t RejectedUnexpectedField = 0;
        size_t RejectedWindowFull = 0;
        std::array<StructureAggregateCensusFieldCounters, 4> FieldCounters{};
        std::array<StructureAggregateCensusVariantBucket, 8> VariantIndexBuckets{};
        size_t VariantIndexOther = 0;
    };

    class StructureAggregateCensus
    {
    public:
        explicit StructureAggregateCensus(StructureAggregateCensusOptions options = {});

        void Configure(StructureAggregateCensusOptions options);
        void Reset();

        bool Accumulate(const StructureEventView& event, bool originalCalled);
        StructureAggregateCensusSnapshot Snapshot() const;

    private:
        bool IsEnabled() const;
        bool IsAcceptedNonPinStructureEvent(const StructureEventView& event) const;
        void CountScalar(const StructureScalarValue& scalar);
        void CountVariantIndex(int32_t value);

        StructureAggregateCensusOptions m_Options;
        StructureAggregateCensusSnapshot m_Snapshot;
    };
}
